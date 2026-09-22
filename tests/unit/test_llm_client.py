"""Regression guards for the OpenAI-compatible LLM client payload shape.

DeepSeek rejects ``response_format.type="json_schema"`` with
HTTP 400 "This response_format type is unavailable now"; it only supports
``{"type": "json_object"}``. ``StructuredLLM`` validates the payload against the
schema client-side, so the client must default to plain JSON mode and carry the
schema in the prompt.
"""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.infrastructure.llm.client import (
    HttpLLMClient,
    LLMError,
    close_llm_client,
    get_llm_client,
    reset_llm_client,
)

SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


def _client(**overrides) -> HttpLLMClient:
    settings = Settings(
        llm_provider="openai_compatible",
        llm_api_base="https://api.example.test/v1",
        llm_api_key="test-key",
        llm_model="deepseek-flash",
        **overrides,
    )
    return HttpLLMClient(settings)


# ---------------------------------------------------------------------------
# Payload shape
# ---------------------------------------------------------------------------
def test_structured_request_defaults_to_json_object() -> None:
    payload = _client()._build_payload(
        "Classify the goal.", system="planner", json_schema=SCHEMA
    )

    assert payload["response_format"] == {"type": "json_object"}
    assert payload["messages"][0] == {"role": "system", "content": "planner"}
    # The word "JSON" is required by json_object mode, and the shape must be visible.
    user_content = payload["messages"][-1]["content"]
    assert "JSON" in user_content
    assert '"ok"' in user_content


def test_json_schema_mode_is_opt_in() -> None:
    payload = _client(llm_response_format="json_schema")._build_payload(
        "Classify the goal.", system=None, json_schema=SCHEMA
    )

    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["schema"] == SCHEMA
    assert payload["messages"][-1]["content"] == "Classify the goal."


def test_plain_completion_sends_no_response_format() -> None:
    payload = _client()._build_payload("hello", system=None, json_schema=None)

    assert "response_format" not in payload
    assert payload["messages"][-1]["content"] == "hello"


def test_invalid_response_format_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(llm_response_format="yaml")


# ---------------------------------------------------------------------------
# HTTP behaviour
# ---------------------------------------------------------------------------
def _with_transport(client: HttpLLMClient, handler) -> HttpLLMClient:
    client._client = httpx.Client(
        base_url="https://api.example.test/v1",
        transport=httpx.MockTransport(handler),
    )
    return client


def test_json_object_request_is_sent_and_parsed() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "deepseek-flash",
                "choices": [{"message": {"role": "assistant", "content": '{"ok": true}'}}],
                "usage": {"total_tokens": 7},
            },
        )

    client = _with_transport(_client(), handler)
    response = client.complete("Return JSON", json_schema=SCHEMA)

    assert response.text == '{"ok": true}'
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["model"] == "deepseek-flash"
    assert "json_schema" not in captured["response_format"]


def test_http_400_raises_llm_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "This response_format type is unavailable now",
                    "type": "invalid_request_error",
                }
            },
        )

    client = _with_transport(_client(), handler)
    with pytest.raises(LLMError):
        client.complete("Return JSON", json_schema=SCHEMA)


# ---------------------------------------------------------------------------
# Process-wide caching / lifecycle
# ---------------------------------------------------------------------------
def test_llm_client_is_cached_for_the_same_settings() -> None:
    reset_llm_client()
    try:
        first = get_llm_client(Settings(llm_provider="mock"))
        second = get_llm_client(Settings(llm_provider="mock"))
        assert first is second
    finally:
        reset_llm_client()


def test_llm_client_is_rebuilt_when_settings_change() -> None:
    reset_llm_client()
    try:
        mock = get_llm_client(Settings(llm_provider="mock"))
        http = get_llm_client(
            Settings(
                llm_provider="openai_compatible",
                llm_api_base="https://api.example.test/v1",
                llm_model="deepseek-flash",
            )
        )
        assert http is not mock
        assert isinstance(http, HttpLLMClient)
        # Switching back must not silently reuse the HTTP client.
        assert get_llm_client(Settings(llm_provider="mock")) is not http
    finally:
        reset_llm_client()


def test_close_llm_client_releases_the_http_pool() -> None:
    reset_llm_client()
    client = get_llm_client(
        Settings(
            llm_provider="openai_compatible",
            llm_api_base="https://api.example.test/v1",
            llm_model="deepseek-flash",
        )
    )
    assert isinstance(client, HttpLLMClient)
    assert client._client.is_closed is False

    close_llm_client()
    assert client._client.is_closed is True

    # Closing is safe to repeat, and rebuilds on next use.
    close_llm_client()
    rebuilt = get_llm_client(Settings(llm_provider="mock"))
    assert rebuilt is not client
    reset_llm_client()
