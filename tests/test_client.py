
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


def test_committed_role_configuration_constructs_offline_without_requests(http):
    client = RoleRoutedClient.from_env(Path(__file__).resolve().parents[1] / "configs/agent_pilot_models.json",
        allow_paid=False, max_cost_usd=.1, environ={"OPENROUTER_API_KEY": "synthetic-key"})
    assert client.planning_client.model == "google/gemini-2.5-flash-lite"
    assert client.review_client.model == "deepseek/deepseek-v3.2"
    assert client.model_settings["roles"]["review"]["reasoning_enabled"] is False
    with pytest.raises(PermissionError):
        make_call(client)
    http.assert_not_called()


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


def test_explicit_json_schema_is_sent_and_bound_to_call_without_changing_defaults(http):
    from moodcut.contracts import json_hash
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}},
              "required": ["ok"], "additionalProperties": False}
    client = live_client()
    assert client.complete_json(stage="actor_revise", system="s", user="u",
        max_output_tokens=100, json_schema=schema) == {"ok": True}
    body = json.loads(http.call_args.args[0].data)
    assert body["response_format"] == {"type": "json_schema", "json_schema": {
        "name": "moodcut_response", "strict": True, "schema": schema}}
    assert client.calls[0]["json_schema_sha256"] == json_hash(schema)
    assert client.calls[0]["response_format_type"] == "json_schema"
    assert body["provider"]["allow_fallbacks"] is False and body["provider"]["require_parameters"] is True


def test_actual_s06_trailing_reply_remains_rejected_with_schema_and_known_cost(http, tmp_path):
    from moodcut.reviewer import get_writer_json_schema
    saved = json.loads((Path(__file__).resolve().parents[1] /
        "docs/pilots/s06-actor-v3.results.json").read_text(encoding="utf-8"))["failed_reply"]
    respond(http, completion(saved["content"], cost=saved["provider_cost_usd"]))
    client = routed_client()
    from moodcut.client import capture_text_responses
    with capture_text_responses(tmp_path):
        with pytest.raises(OpenRouterError, match="syntax_error"):
            client.complete_json(stage="actor_revise", system="s", user="u",
                max_output_tokens=2048, json_schema=get_writer_json_schema())
    call = client.calls[0]
    assert call["parse_error"] == saved["parse_error"] and call["provider_cost_usd"] == saved["provider_cost_usd"]
    assert (tmp_path / call["response_artifact"]["content_path"]).read_text(encoding="utf-8") == saved["content"]
    assert client.stopped
    with pytest.raises(BudgetError):
        make_call(client)
    assert http.call_count == 1


@pytest.mark.parametrize("schema", [[], {"type": "array"}, {"type": "object", "bad": float("nan")},
                                    {"type": "object", 1: {}}])
def test_invalid_schema_stops_before_transport_or_call_record(http, schema):
    client = live_client()
    with pytest.raises(ValueError):
        client.complete_json(stage="actor_revise", system="s", user="u", max_output_tokens=10,
                             json_schema=schema)
    assert client.calls == []
    http.assert_not_called()


def test_schema_size_is_included_in_shared_budget_reservation(http):
    from moodcut.reviewer import get_writer_json_schema
    planning = live_client()
    review = live_client()
    _, old_reservation = planning._reservation("s", "u", 10)
    client = RoleRoutedClient(planning, review, max_cost_usd=float(old_reservation))
    with pytest.raises(BudgetError):
        client.complete_json(stage="actor_revise", system="s", user="u", max_output_tokens=10,
                             json_schema=get_writer_json_schema())
    assert client.calls == [] and client.stopped
    http.assert_not_called()


def test_schema_unsupported_response_never_downgrades_or_retries(http):
    from moodcut.reviewer import get_writer_json_schema
    http.side_effect = HTTPError("https://example.invalid", 400, "unsupported", {},
        io.BytesIO(json.dumps({"error": {"message": "schema unsupported"}, "usage": {"cost": 0}}).encode()))
    client = routed_client()
    with pytest.raises(OpenRouterError, match="HTTP 400"):
        client.complete_json(stage="actor_revise", system="s", user="u", max_output_tokens=100,
                             json_schema=get_writer_json_schema())
    assert client.calls[0]["provider_cost_usd"] == 0 and client.stopped
    with pytest.raises(BudgetError):
        make_call(client)
    body = json.loads(http.call_args.args[0].data)
    assert body["response_format"]["type"] == "json_schema" and http.call_count == 1
    assert "plugins" not in body and "tools" not in body


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


@pytest.mark.parametrize("content,kind", [('{"x":', 'syntax_error'), ('{"x":1,"x":2}', 'duplicate_key'),
    ('{"x":NaN}', 'non_finite'), ('{"x":1e999}', 'non_finite'), ('[]', 'non_object'), ('null', 'non_object')])
def test_invalid_content_is_saved_before_parsing_with_specific_diagnostic(http, tmp_path, content, kind):
    import hashlib
    raw = json.dumps(completion(content), ensure_ascii=False).encode()
    http.side_effect = lambda *a, **k: io.BytesIO(raw)
    client = live_client(response_dir=tmp_path)
    with pytest.raises(OpenRouterError):
        make_call(client)
    record = client.calls[0]
    assert record["parse_error"]["layer"] == "content" and record["parse_error"]["kind"] == kind
    artifact = record["response_artifact"]
    body = tmp_path / artifact["body_path"]
    assert body.read_bytes() == raw and hashlib.sha256(raw).hexdigest() == artifact["body_sha256"]
    assert (tmp_path / artifact["content_path"]).read_text(encoding="utf-8") == content
    diagnostic = json.loads((body.parent / "diagnostic.json").read_text(encoding="utf-8"))
    assert diagnostic["parse_error"] == record["parse_error"] and diagnostic["provider_cost_usd"] == .001
    assert record["provider_cost_usd"] == .001 and http.call_count == 1
    assert not any(k in record for k in ("body", "content", "raw_response"))
    if kind == "syntax_error":
        assert record["parse_error"]["line"] == 1 and record["parse_error"]["column"] > 0


@pytest.mark.parametrize("raw,kind", [(b'{"broken":', "syntax_error"), (b'\xff', "invalid_utf8"),
    (b'{"usage":1,"usage":2}', "duplicate_key"), (b'{"cost":Infinity}', "non_finite"),
    (b'{"cost":1e999}', "non_finite"), (b'[]', 'non_object')])
def test_envelope_errors_retain_exact_bytes_and_unknown_charge_blocks_next_call(http, tmp_path, raw, kind):
    http.side_effect = lambda *a, **k: io.BytesIO(raw)
    client = live_client(response_dir=tmp_path)
    with pytest.raises(OpenRouterError): make_call(client)
    record = client.calls[0]
    assert record["parse_error"]["layer"] == "envelope"
    assert record["parse_error"]["kind"] == kind
    assert (tmp_path / record["response_artifact"]["body_path"]).read_bytes() == raw
    assert "content_path" not in record["response_artifact"] and client.spent_usd is None
    with pytest.raises(BudgetError): make_call(client)
    assert http.call_count == 1


def test_body_exists_before_json_parser_is_entered(http, tmp_path, monkeypatch):
    import moodcut.client as module
    raw = json.dumps(completion('{"x":')).encode()
    http.side_effect = lambda *a, **k: io.BytesIO(raw)
    strict = module._strict_json
    inspected = []
    def inspect(text):
        files = list(tmp_path.rglob('response.bin'))
        assert len(files) == 1 and files[0].read_bytes() == raw
        if text == '{"x":':
            assert files[0].with_name('content.txt').read_text() == text
        inspected.append(True)
        return strict(text)
    monkeypatch.setattr(module, '_strict_json', inspect)
    with pytest.raises(OpenRouterError): make_call(live_client(response_dir=tmp_path))
    assert len(inspected) == 2


def test_private_artifacts_redact_echoed_key_without_storing_headers(http, tmp_path):
    content = '{"message":"test-secret-not-real", "unfinished":'
    raw = json.dumps(completion(content)).encode()
    http.side_effect = lambda *a, **k: io.BytesIO(raw)
    client = live_client(response_dir=tmp_path)
    with pytest.raises(OpenRouterError): make_call(client)
    files = list(tmp_path.rglob('*'))
    assert all(b'test-secret-not-real' not in p.read_bytes() for p in files if p.is_file())
    assert 'test-secret-not-real' not in json.dumps(client.calls)
    artifact = client.calls[0]['response_artifact']
    assert artifact['credential_redacted'] and artifact['content_credential_redacted']
    assert b'[REDACTED]' in (tmp_path / artifact['content_path']).read_bytes()
    assert not any('headers' in p.name for p in files)


def test_http_error_raw_body_and_known_charge_are_retained(http, tmp_path):
    raw = b'{"error":{"message":"test-secret-not-real"},"usage":{"cost":0.0002}}'
    http.side_effect = HTTPError('https://example.invalid', 429, 'failure', {}, io.BytesIO(raw))
    client = live_client(response_dir=tmp_path)
    with pytest.raises(OpenRouterError, match='429'): make_call(client)
    record = client.calls[0]
    assert record['http_status'] == 429 and record['provider_cost_usd'] == .0002
    assert (tmp_path / record['response_artifact']['body_path']).read_bytes() == raw.replace(b'test-secret-not-real',b'[REDACTED]')
    assert http.call_count == 1


def test_oversize_body_is_a_marked_prefix_not_a_complete_response(http, tmp_path):
    http.side_effect = lambda *a, **k: io.BytesIO(b'x'*80)
    client = live_client(response_dir=tmp_path);client.MAX_RESPONSE_BYTES=32
    with pytest.raises(OpenRouterError, match='size limit'): make_call(client)
    artifact = client.calls[0]['response_artifact']
    assert artifact['body_bytes'] == 33 and artifact['complete'] is False
    assert client.spent_usd is None and http.call_count == 1


@pytest.mark.parametrize("filename,kind", [("response.bin", "body_write_failed"),
                                         ("content.txt", "content_write_failed")])
def test_retention_write_failure_stops_valid_result_but_retains_cost(http, tmp_path, monkeypatch, filename, kind):
    original = Path.open
    def refuse(path, *a, **k):
        if path.name == filename: raise OSError('private filesystem message')
        return original(path,*a,**k)
    monkeypatch.setattr(Path, 'open', refuse)
    client = live_client(response_dir=tmp_path)
    with pytest.raises(OpenRouterError, match='could not be retained'): make_call(client)
    record=client.calls[0]
    assert record['retention_error']==kind and record['provider_cost_usd']==.001
    assert record['status']=='invalid_response' and 'private filesystem message' not in json.dumps(record)


def test_capture_context_is_restored_and_artifacts_are_never_overwritten(http, tmp_path):
    from moodcut.client import capture_text_responses
    client = live_client()
    with capture_text_responses(tmp_path/'one'):
        assert make_call(client)=={'ok':True}
        with capture_text_responses(tmp_path/'two'):
            make_call(client)
        make_call(client)
    make_call(client)
    assert len(list((tmp_path/'one').rglob('response.bin')))==2
    assert len(list((tmp_path/'two').rglob('response.bin')))==1
    assert client.calls[-1]['response_artifact'] is None and http.call_count==4


def test_invalid_content_unknown_cost_is_preserved_and_remains_unknown(http, tmp_path):
    respond(http, completion('{', cost=None))
    client=live_client(response_dir=tmp_path)
    with pytest.raises(OpenRouterError): make_call(client)
    record=client.calls[0]
    assert record['parse_error']['kind']=='syntax_error' and client.spent_usd is None
    assert (tmp_path / record['response_artifact']['content_path']).read_text()=='{'
    with pytest.raises(BudgetError): make_call(client)
    assert http.call_count==1


def test_deep_content_has_its_own_diagnostic(http, tmp_path):
    content='['*2000+'0'+']'*2000
    respond(http,completion(content))
    client=live_client(response_dir=tmp_path)
    with pytest.raises(OpenRouterError): make_call(client)
    assert client.calls[0]['parse_error']=={'layer':'content','kind':'excessive_nesting'}
    assert client.calls[0]['provider_cost_usd']==.001


@pytest.mark.parametrize("invalid_content", [False, True])
def test_metadata_write_failure_stops_success_without_masking_primary_error(http, tmp_path, monkeypatch, invalid_content):
    original=Path.open
    def refuse(path,*a,**k):
        if path.name=='diagnostic.json':raise OSError('private filesystem message')
        return original(path,*a,**k)
    monkeypatch.setattr(Path,'open',refuse)
    if invalid_content:
        respond(http, completion('{'))
    client=live_client(response_dir=tmp_path)
    expected = 'syntax_error' if invalid_content else 'diagnostic could not be saved'
    with pytest.raises(OpenRouterError,match=expected):make_call(client)
    record=client.calls[0]
    assert record['status']==('invalid_response' if invalid_content else 'retention_failed')
    assert record['retention_error']=='diagnostic_write_failed'
    assert record['provider_cost_usd']==.001 and http.call_count==1
    assert (tmp_path / record['response_artifact']['body_path']).exists()


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
