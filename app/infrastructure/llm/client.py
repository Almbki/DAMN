"""LLM client implementations.

``LLMClient`` is a structural protocol - application code depends on it, not on
any concrete HTTP implementation. The default provider is deterministic
:class:`MockLLMClient`; switching happens through ``settings.llm_provider``.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


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

    def close(self) -> None:
        """Release the underlying HTTP connection pool (idempotent)."""
        self._client.close()

    def _build_payload(
        self,
        prompt: str,
        *,
        system: str | None,
        json_schema: dict | None,
    ) -> dict[str, Any]:
        """Build the OpenAI-compatible chat-completions payload."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})

        user_content = prompt
        payload: dict[str, Any] = {"model": self._settings.llm_model}
        if json_schema is not None:
            if self._settings.llm_response_format == "json_schema":
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": "response", "strict": True, "schema": json_schema},
                }
            else:
                # Plain JSON mode. DeepSeek rejects response_format.type
                # "json_schema" with HTTP 400 ("This response_format type is
                # unavailable now"), so the schema travels in the prompt and
                # StructuredLLM enforces it by validating + retrying. OpenAI-style
                # json_object mode requires the word "JSON" to appear in the input.
                payload["response_format"] = {"type": "json_object"}
                user_content = (
                    f"{prompt}\n\n"
                    "Return a single JSON object that matches the JSON schema below. "
                    "Output JSON only - no prose, no markdown, no code fences.\n"
                    f"{json.dumps(json_schema, ensure_ascii=False)}"
                )
        messages.append({"role": "user", "content": user_content})
        payload["messages"] = messages
        return payload

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        payload = self._build_payload(prompt, system=system, json_schema=json_schema)

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


#: Process-wide cache so the HTTP client (and its keep-alive connection pool) is
#: built once instead of per request. ``get_plan_service`` runs for every request,
#: so a fresh ``httpx.Client`` there meant a full TCP+TLS handshake each time and
#: a socket left unclosed.
_llm_client: LLMClient | None = None
_llm_client_key: tuple[Any, ...] | None = None
_llm_client_lock = threading.Lock()


def _client_key(settings: Settings) -> tuple[Any, ...]:
    """Cache key: any config change must invalidate the cached client."""
    return (
        (settings.llm_provider or "mock").strip().lower(),
        settings.llm_api_base,
        settings.llm_api_key,
        settings.llm_model,
        settings.llm_timeout_seconds,
        settings.llm_response_format,
    )


def _build_llm_client(settings: Settings) -> LLMClient:
    provider = (settings.llm_provider or "mock").strip().lower()
    if provider in {"mock", "dummy"}:
        return MockLLMClient()
    return HttpLLMClient(settings)


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    """Return the process-wide LLM client selected by ``settings.llm_provider``.

    ``mock``/``dummy`` -> :class:`MockLLMClient`; everything else falls back to
    the HTTP/OpenAI-compatible client. The instance is cached (and thread-safe)
    so connections are reused across requests; call :func:`close_llm_client` from
    the application lifespan to release the pool.
    """
    global _llm_client, _llm_client_key
    settings = settings or get_settings()
    key = _client_key(settings)
    with _llm_client_lock:
        if _llm_client is None or _llm_client_key != key:
            _close_quietly(_llm_client)
            _llm_client = _build_llm_client(settings)
            _llm_client_key = key
        return _llm_client


def _close_quietly(client: LLMClient | None) -> None:
    close = getattr(client, "close", None)
    if not callable(close):
        return
    try:
        close()
    except Exception as exc:  # noqa: BLE001 - shutdown must never raise
        logger.warning("llm client close failed: %s: %s", type(exc).__name__, exc)


def close_llm_client() -> None:
    """Close and drop the cached LLM client. Safe to call more than once."""
    global _llm_client, _llm_client_key
    with _llm_client_lock:
        client, _llm_client = _llm_client, None
        _llm_client_key = None
    _close_quietly(client)


def reset_llm_client() -> None:
    """Drop the cached LLM client (used by tests)."""
    close_llm_client()


__all__ = [
    "HttpLLMClient",
    "LLMClient",
    "LLMError",
    "LLMResponse",
    "MockLLMClient",
    "close_llm_client",
    "get_llm_client",
    "reset_llm_client",
]