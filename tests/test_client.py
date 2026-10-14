
"""Unit tests for MoodCut FakeClient."""

import pytest

from moodcut.client import FakeClient, LLMClient


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
