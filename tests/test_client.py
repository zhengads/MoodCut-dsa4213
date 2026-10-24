
"""Offline FakeClient and OpenRouter checks with hand-written HTTP fixtures."""

import io
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest

from moodcut.client import BudgetError, FakeClient, LLMClient, OpenRouterClient, OpenRouterError, RoleRoutedClient


def make_call(client):
    """Helper function for calling the client."""
    return client.complete_json(
        stage="director",
        system="You are a director.",
        user="Create a movie scene.",
        max_output_tokens=500,
    )


def test_returns_predefined_response():
    client = FakeClient([
        {"message": "Hello MoodCut"}
    ])

    result = make_call(client)

    assert result == {"message": "Hello MoodCut"}
    assert client.remaining == 0


def test_responses_are_returned_in_order():
    client = FakeClient([
        {"step": 1},
        {"step": 2},
        {"step": 3},
    ])

    assert make_call(client) == {"step": 1}
    assert make_call(client) == {"step": 2}
    assert make_call(client) == {"step": 3}
    assert client.remaining == 0


def test_records_call_information():
    client = FakeClient([{"ok": True}])

    make_call(client)

    assert len(client.calls) == 1
    assert client.calls[0]["stage"] == "director"
    assert client.calls[0]["max_output_tokens"] == 500
    assert client.calls[0]["system"] == "You are a director."
    assert client.calls[0]["user"] == "Create a movie scene."


def test_empty_queue_raises_error():
    client = FakeClient([])

    with pytest.raises(RuntimeError, match="exhausted"):
        make_call(client)


def test_invalid_stage_raises_error():
    client = FakeClient([{"ok": True}])

    with pytest.raises(ValueError, match="stage"):
        client.complete_json(
            stage="",
            system="system",
            user="user",
            max_output_tokens=100,
        )


def test_invalid_token_limit_raises_error():
    client = FakeClient([{"ok": True}])

    with pytest.raises(ValueError, match="max_output_tokens"):
        client.complete_json(
            stage="director",
            system="system",
            user="user",
            max_output_tokens=-1,
        )


def test_invalid_response_type_raises_error():
    client = FakeClient(["not a dictionary"])

    with pytest.raises(TypeError, match="dictionary"):
        make_call(client)


def test_non_json_response_raises_error():
    client = FakeClient([
        {"invalid": {1, 2, 3}}
    ])

    with pytest.raises(ValueError, match="valid JSON"):
        make_call(client)


def test_response_is_independent_of_original():
    original = [{"items": [1, 2]}]
    client = FakeClient(original)

    original[0]["items"].append(3)

    result = make_call(client)

    assert result == {"items": [1, 2]}

    result["items"].append(99)

    assert original[0]["items"] == [1, 2, 3]


def test_fake_client_implements_interface():
    client = FakeClient([{"ok": True}])

    assert isinstance(client, LLMClient)



def test_fake_client_never_uses_network(monkeypatch):
    """FakeClient must work without network access."""

    import socket
    import urllib.request

    def block_network(*args, **kwargs):
        raise AssertionError(
            "FakeClient attempted to access the network"
        )

    # Block common Python networking entry points.
    monkeypatch.setattr(
        socket.socket,
        "connect",
        block_network,
    )

    monkeypatch.setattr(
        socket,
        "create_connection",
        block_network,
    )

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        block_network,
    )

    client = FakeClient([
        {"message": "Offline response"}
    ])

    result = client.complete_json(
        stage="director",
        system="You are a director.",
        user="Create a scene.",
        max_output_tokens=500,
    )

    assert result == {
        "message": "Offline response"
    }

    assert len(client.calls) == 1
    assert client.remaining == 0


def completion(content='{"ok": true}', *, cost=0.001, **changes):
    response = {
        "id": "gen-test", "model": "vendor/test-model",
        "choices": [{"finish_reason": "stop", "message": {"content": content}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": cost},
    }
    response.update(changes)
    return response


@pytest.fixture
def http(monkeypatch):
    send = Mock(side_effect=lambda *a, **kw: io.BytesIO(json.dumps(completion()).encode()))
    monkeypatch.setattr("moodcut.client.build_opener", Mock(return_value=Mock(open=send)))
    return send


def live_client(**kwargs):
    return OpenRouterClient(
        api_key="test-secret-not-real", model="vendor/test-model",
        input_price_per_million=1, output_price_per_million=2,
        **{"allow_paid": True, "max_cost_usd": 0.1, **kwargs},
    )


def respond(http, response):
    http.side_effect = lambda *a, **kw: io.BytesIO(json.dumps(response).encode())


def routed_client():
    clients = [OpenRouterClient(api_key="synthetic-key", model=model,
        input_price_per_million=1, output_price_per_million=2, reasoning_enabled=False,
        allow_paid=True, max_cost_usd=.1) for model in ("test/planning", "test/review")]
    return RoleRoutedClient(*clients, max_cost_usd=.1)


def test_role_routing_uses_actual_models_and_explicit_reasoning_control(http):
    client = routed_client()
    for stage in ("director", "scene", "shot", "critique", "revise", "verify", "critique"):
        client.complete_json(stage=stage, system="s", user="u", max_output_tokens=10)
    bodies = [json.loads(c.args[0].data) for c in http.call_args_list]
    assert [b["model"] for b in bodies] == ["test/planning"] * 3 + ["test/review"] * 4
    assert all(b["reasoning"] == {"enabled": False} for b in bodies)
    assert [c["model_id"] for c in client.calls] == [b["model"] for b in bodies]
    assert client.spent_usd == pytest.approx(.007)
    assert client.model.startswith("role-policy/")


def test_role_budget_is_shared_and_cannot_be_spent_twice(http):
    client = routed_client()
    respond(http, completion(cost=.099))
    make_call(client)
    with pytest.raises(BudgetError):
        client.complete_json(stage="critique", system="s", user="u", max_output_tokens=1000)
    assert http.call_count == 1 and client.stopped
    with pytest.raises(BudgetError):
        make_call(client)
    assert http.call_count == 1


@pytest.mark.parametrize("response", [completion(cost=None), completion(content="not JSON"),
                                      completion(cost=.11)])
def test_role_failure_or_unknown_charge_blocks_every_later_role(http, response):
    client = routed_client()
    respond(http, response)
    with pytest.raises((OpenRouterError, BudgetError)):
        make_call(client)
    with pytest.raises(BudgetError):
        client.complete_json(stage="critique", system="s", user="u", max_output_tokens=10)
    assert http.call_count == len(client.calls) == 1


def test_role_policy_identity_binds_both_models_and_controls(http):
    client = routed_client()
    before = client.model
    client.review_client.model = "test/other-review"
    assert client.model != before
    before = client.model
    client.review_client.reasoning_enabled = True
    assert client.model != before
    with pytest.raises(ValueError, match="Unknown text stage"):
        client.complete_json(stage="other", system="s", user="u", max_output_tokens=10)
    http.assert_not_called()


def test_openrouter_request_and_accounting(http):
    client = live_client()
    assert isinstance(client, LLMClient)
    assert make_call(client) == {"ok": True}
    request = http.call_args.args[0]
    body = json.loads(request.data)
    assert request.full_url == "https://openrouter.ai/api/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer test-secret-not-real"
    assert body["model"] == "vendor/test-model"
    assert body["max_tokens"] == 500 and body["stream"] is False
    assert body["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert body["provider"]["max_price"] == {"prompt": 1, "completion": 2, "request": 0}
    assert body["provider"]["allow_fallbacks"] is False
    assert body["provider"]["require_parameters"] is True
    record = client.calls[0]
    assert record["status"] == "success" and record["stage"] == "director"
    assert record["input_tokens"] == 100 and record["output_tokens"] == 20
    assert record["provider_cost_usd"] == 0.001
    assert record["estimated_cost_usd"] == pytest.approx(0.00014)
    assert record["generation_id"] == "gen-test" and record["elapsed_s"] >= 0
    assert "test-secret-not-real" not in json.dumps(client.calls)
    assert client.spent_usd == pytest.approx(0.001)


def test_paid_disabled_and_budget_preflight_do_not_send(http):
    with pytest.raises(PermissionError):
        make_call(live_client(allow_paid=False))
    client = live_client(max_cost_usd=0.000001)
    with pytest.raises(BudgetError):
        make_call(client)
    http.assert_not_called()
    assert client.calls == []


def test_actual_charge_blocks_next_request(http):
    client = live_client(max_cost_usd=0.0015)
    make_call(client)
    with pytest.raises(BudgetError):
        make_call(client)
    assert http.call_count == 1


@pytest.mark.parametrize("field,value", [
    ("max_cost_usd", None), ("max_cost_usd", 0), ("max_cost_usd", float("nan")),
    ("input_price_per_million", None), ("output_price_per_million", -1),
    ("input_price_per_million", True), ("timeout_s", 0), ("temperature", float("inf")),
    ("model", ""), ("api_key", ""),
])
def test_invalid_configuration_fails_before_network(http, field, value):
    config = dict(api_key="test-secret-not-real", model="vendor/test-model",
                  input_price_per_million=1, output_price_per_million=2,
                  allow_paid=True, max_cost_usd=0.1)
    config[field] = value
    with pytest.raises((TypeError, ValueError)):
        OpenRouterClient(**config)
    http.assert_not_called()


@pytest.mark.parametrize("field,value", [
    ("stage", " "), ("system", None), ("user", []),
    ("max_output_tokens", True), ("max_output_tokens", 0),
])
def test_openrouter_invalid_request_is_local(http, field, value):
    args = dict(stage="shot", system="JSON only", user="test", max_output_tokens=20)
    args[field] = value
    with pytest.raises((TypeError, ValueError)):
        live_client().complete_json(**args)
    http.assert_not_called()


@pytest.mark.parametrize("content", ["not JSON", "[]", "null", '{"x":NaN}', '{"x":1e999}', '{"x":1,"x":2}'])
def test_invalid_model_json_retains_known_cost(http, content):
    respond(http, completion(content))
    client = live_client()
    with pytest.raises(OpenRouterError):
        make_call(client)
    assert http.call_count == 1
    assert client.calls[0]["status"] == "invalid_response"
    assert client.calls[0]["provider_cost_usd"] == 0.001
    assert client.spent_usd == pytest.approx(0.001)


@pytest.mark.parametrize("finish", ["length", "content_filter", "tool_calls", "error", None])
def test_incomplete_output_is_not_accepted_even_if_json_parses(http, finish):
    response = completion()
    response["choices"][0]["finish_reason"] = finish
    respond(http, response)
    with pytest.raises(OpenRouterError):
        make_call(live_client())
    assert http.call_count == 1


def test_missing_cost_is_unknown_and_blocks_later_calls(http):
    response = completion()
    del response["usage"]["cost"]
    respond(http, response)
    client = live_client()
    assert make_call(client) == {"ok": True}
    assert client.calls[0]["provider_cost_usd"] is None
    assert client.spent_usd is None
    assert client.calls[0]["estimated_cost_usd"] == pytest.approx(0.00014)
    with pytest.raises(BudgetError, match="unknown"):
        make_call(client)
    assert http.call_count == 1


def test_missing_usage_does_not_invent_zero(http):
    response = completion()
    del response["usage"]
    respond(http, response)
    client = live_client()
    assert make_call(client) == {"ok": True}
    for field in ("input_tokens", "output_tokens", "estimated_cost_usd", "provider_cost_usd"):
        assert client.calls[0][field] is None


@pytest.mark.parametrize("failure", [TimeoutError("secret and prompt"), URLError("secret and prompt")])
def test_transport_failure_has_no_retry_or_secret_in_error(http, failure):
    http.side_effect = failure
    client = live_client()
    with pytest.raises(OpenRouterError) as error:
        make_call(client)
    assert "secret and prompt" not in str(error.value)
    assert http.call_count == 1
    assert client.calls[0]["provider_cost_usd"] is None
    with pytest.raises(BudgetError):
        make_call(client)


@pytest.mark.parametrize("status", [401, 402, 429, 500])
def test_http_error_is_single_attempt_and_sanitized(http, status):
    body = json.dumps({"error": {"message": "test-secret-not-real"},
                       "usage": {"cost": 0.0001}}).encode()
    http.side_effect = HTTPError("https://openrouter.ai", status, "error", {}, io.BytesIO(body))
    client = live_client()
    with pytest.raises(OpenRouterError) as error:
        make_call(client)
    assert str(status) in str(error.value)
    assert "test-secret-not-real" not in str(error.value)
    assert client.calls[0]["http_status"] == status
    assert client.calls[0]["provider_cost_usd"] == 0.0001
    assert http.call_count == 1


def test_in_band_error_and_bad_envelope_are_not_model_results(http):
    for response in ({"error": {"code": 502, "message": "private"}}, [], {"choices": []}):
        respond(http, response)
        with pytest.raises(OpenRouterError):
            make_call(live_client())


def test_from_env_reads_config_and_does_not_auto_authorize(http, tmp_path):
    path = tmp_path / "model.json"
    path.write_text(json.dumps(dict(model="vendor/test-model", input_price_per_million=1,
                                   output_price_per_million=2, temperature=0, timeout_s=20)))
    client = OpenRouterClient.from_env(path, environ={"OPENROUTER_API_KEY": "test-secret-not-real"},
                                      max_cost_usd=0.1)
    with pytest.raises(PermissionError):
        make_call(client)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        OpenRouterClient.from_env(path, environ={}, max_cost_usd=0.1)
    http.assert_not_called()


def test_real_client_contract_runs_existing_reviewer_offline(http):
    from moodcut.reviewer import review_and_revise

    fixtures = Path(__file__).parent / "fixtures"
    read = lambda name: json.loads((fixtures / f"{name}.json").read_text(encoding="utf-8"))
    reports = [read("review"), read("patch"), read("verification")]
    http.side_effect = [io.BytesIO(json.dumps(completion(json.dumps(r))).encode()) for r in reports]
    client = live_client()
    plan = read("plan")
    original = deepcopy(plan)
    result = review_and_revise(read("scene"), plan, read("assets"), client, mode="moodcut")
    assert result["status"] == "applied", result["errors"]
    assert plan == original
    assert [r["stage"] for r in client.calls] == ["critique", "revise", "verify"]
    assert client.spent_usd == pytest.approx(0.003)
    payloads = [json.loads(c.args[0].data) for c in http.call_args_list]
    assert all(len(p["messages"]) == 2 for p in payloads)


def test_check_client_command_validates_without_request(http, tmp_path, monkeypatch, capsys):
    from moodcut.__main__ import main

    path = tmp_path / "config.json"
    path.write_text(json.dumps(dict(model="vendor/test-model", input_price_per_million=1,
                                   output_price_per_million=2)))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-secret-not-real")
    monkeypatch.setattr("sys.argv", ["moodcut", "check-client", "--config", str(path),
                                    "--max-cost-usd", "0.1"])
    assert main() == 0
    output = capsys.readouterr().out
    assert "no network request" in output
    assert "test-secret-not-real" not in output
    http.assert_not_called()


def test_bad_check_client_does_not_echo_secret_config(http, tmp_path, monkeypatch, capsys):
    from moodcut.__main__ import main

    path = tmp_path / "bad.json"
    path.write_text("private-value-not-for-output")
    monkeypatch.setattr("sys.argv", ["moodcut", "check-client", "--config", str(path),
                                    "--max-cost-usd", "0.1"])
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 2
    assert "private-value-not-for-output" not in capsys.readouterr().err
    http.assert_not_called()


def test_redirects_are_refused_before_forwarding_auth():
    from moodcut.client import _NoRedirect
    from urllib.request import Request

    request = Request(OpenRouterClient.ENDPOINT, headers={"Authorization": "Bearer private"})
    assert _NoRedirect().redirect_request(request, None, 302, "redirect", {}, "https://other.example") is None
