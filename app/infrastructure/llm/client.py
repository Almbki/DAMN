"""LLM client implementations.

``LLMClient`` is a structural protocol - application code depends on it, not on
any concrete HTTP implementation. The default provider is deterministic
:class:`MockLLMClient`; switching happens through ``settings.llm_provider``.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings


class LLMError(RuntimeError):
    """Raised when a real LLM request fails or its response is malformed."""


class LLMResponse(BaseModel):
    """Normalised completion result regardless of provider."""

    text: str
    model: str
    usage: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMClient(Protocol):
    """Synchronous OpenAI-compatible chat completion interface."""

    name: str

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        """Complete ``prompt`` (optionally with a system message).

        When ``json_schema`` is provided the provider is asked for a JSON
        response matching that structure.
        """
        ...


class MockLLMClient:
    """Deterministic stub - MOCK, no real LLM call is ever made.

    Used for development / tests. Returns a fixed, reproducible payload so
    services can be run and exercised offline.
    """

    name: str = "mock"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        if json_schema is not None:
            text = json.dumps({"scaffold": {"created_by": "MockLLMClient", "schema": json_schema}})
        elif prompt:
            text = f"[mock] {prompt[:512]}"
        else:
            text = "[mock]"
        return LLMResponse(
            text=text,
            model="mock-model",
            usage={"prompt_tokens": 0, "completion_tokens": len(text), "total_tokens": len(text)},
            raw={"provider": "mock", "system": system, "json_schema": json_schema},
        )


class HttpLLMClient:
    """OpenAI-compatible ``/chat/completions`` client over httpx (SYNC).

    Uses ``settings.llm_api_base`` (defaults to the OpenAI endpoint), API key
    from ``settings.llm_api_key`` and ``settings.llm_model``.
    """

    name: str = "http"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        base_url = self._settings.llm_api_base or "https://api.openai.com/v1"
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=settings.llm_timeout_seconds,
            headers=headers,
        )

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {"model": self._settings.llm_model, "messages": messages}
        if json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "strict": True, "schema": json_schema},
            }

        try:
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc
        except ValueError as exc:  # non-JSON response body
            raise LLMError(f"LLM returned a non-JSON response: {exc}") from exc

        if not isinstance(data, dict):
            raise LLMError(f"LLM response not an object: {data!r}")

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"LLM response missing completion content: {data!r}") from exc

        usage = data.get("usage")
        if not isinstance(usage, dict):
            usage = {}
        model = data.get("model", self._settings.llm_model)
        return LLMResponse(text=text, model=str(model), usage=usage, raw=data)


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    """Build the LLM client selected by ``settings.llm_provider``.

    ``mock``/``dummy`` -> :class:`MockLLMClient`; everything else falls back to
    the HTTP/OpenAI-compatible client.
    """
    settings = settings or get_settings()
    provider = (settings.llm_provider or "mock").strip().lower()
    if provider in {"mock", "dummy"}:
        return MockLLMClient()
    return HttpLLMClient(settings)