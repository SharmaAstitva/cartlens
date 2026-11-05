"""Unit tests for the Groq client, using httpx.MockTransport (no network)."""

import json

import httpx
import pytest

from app.llm import GroqClient, LLMError, parse_json

SCHEMA = {"type": "object", "properties": {"sql": {"type": "string"}}}


def client_with(handler):
    return GroqClient(
        "test-key", "openai/gpt-oss-120b", http=httpx.Client(transport=httpx.MockTransport(handler))
    )


def ok_response(content: str):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_sends_model_schema_and_key():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return ok_response('{"sql": "select 1"}')

    out = client_with(handler).complete_json("system prompt", "user prompt", SCHEMA)
    assert out == {"sql": "select 1"}
    assert seen["auth"] == "Bearer test-key"
    body = seen["body"]
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["temperature"] == 0
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"] == SCHEMA
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_http_error_becomes_llm_error():
    client = client_with(lambda r: httpx.Response(429, text="rate limited"))
    with pytest.raises(LLMError, match="429"):
        client.complete_json("s", "u", SCHEMA)


def test_network_error_becomes_llm_error():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(LLMError, match="reach"):
        client_with(handler).complete_json("s", "u", SCHEMA)


def test_unexpected_shape_becomes_llm_error():
    client = client_with(lambda r: httpx.Response(200, json={"oops": True}))
    with pytest.raises(LLMError):
        client.complete_json("s", "u", SCHEMA)


def test_parse_json_strips_code_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


@pytest.mark.parametrize("text", ["not json", "[1, 2]", ""])
def test_parse_json_rejects_non_objects(text):
    with pytest.raises(LLMError):
        parse_json(text)
