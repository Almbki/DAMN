"""Structured LLM access.

Nodes never call the raw client. They go through :class:`StructuredLLM`, which:

1. loads the prompt file for the step,
2. asks the client for JSON matching the Pydantic schema,
3. validates the payload into the schema,
4. feeds validation errors back and retries (bounded),
5. falls back to a deterministic value when the LLM is absent or keeps failing.

Every call reports ``used_llm`` / ``source`` truthfully so nothing can pretend
an LLM produced a result it did not.

The client is duck-typed (``complete(prompt, *, system, json_schema)``) so this
module imports no infrastructure code at runtime.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.agent.prompts import load_prompt

if TYPE_CHECKING:  # pragma: no cover
    from app.infrastructure.llm.client import LLMClient

TModel = TypeVar("TModel", bound=BaseModel)

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(slots=True)
class StructuredResult(Generic[TModel]):  # noqa: UP046 - PEP 695 params break F821 here
    """Outcome of one structured LLM call."""

    value: TModel
    used_llm: bool = False
    source: str = "fallback"
    attempts: int = 0
    duration_ms: int = 0
    error: str | None = None

    @property
    def degraded(self) -> bool:
        return not self.used_llm


def _extract_json(text: str) -> str:
    """Pull a JSON object out of a possibly chatty LLM response."""
    fenced = _CODE_FENCE_RE.search(text)
    if fenced:
        return fenced.group(1).strip()
    match = _JSON_OBJECT_RE.search(text)
    return match.group(0) if match else text.strip()


def _matches_schema_fields(payload: object, schema: type[BaseModel]) -> bool:
    """Guard against a valid-looking but unrelated payload.

    Even with ``extra="forbid"``, a response that happens to be ``{}`` would
    validate against an all-optional schema. Requiring at least one of the
    schema's own fields to be present forces the fallback instead.
    """
    if not isinstance(payload, dict):
        return False
    return bool(set(schema.model_fields) & set(payload))


class StructuredLLM:
    """Schema-validated LLM calls with retry and deterministic fallback."""

    def __init__(
        self,
        client: LLMClient | None = None,
        *,
        max_retries: int = 2,
        prompt_version: str = "v1",
    ) -> None:
        self._client = client
        self.max_retries = max(0, max_retries)
        self.prompt_version = prompt_version
        self.calls = 0

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def complete_model(
        self,
        *,
        prompt_name: str,
        schema: type[TModel],
        variables: dict[str, object],
        fallback: TModel,
    ) -> StructuredResult[TModel]:
        """Return a validated ``schema`` instance, or the fallback (never raises)."""
        started = time.perf_counter()
        if self._client is None:
            return StructuredResult(
                value=fallback,
                used_llm=False,
                source="fallback:no_llm",
                duration_ms=0,
                error=None,
            )

        try:
            template = load_prompt(prompt_name)
        except FileNotFoundError as exc:
            return StructuredResult(
                value=fallback,
                used_llm=False,
                source="fallback:missing_prompt",
                duration_ms=0,
                error=str(exc),
            )

        schema_json = schema.model_json_schema()
        extra = ""
        last_error: str | None = None

        for attempt in range(1, self.max_retries + 2):
            prompt = template.render(**variables) + extra
            try:
                self.calls += 1
                response = self._client.complete(
                    prompt, system=template.meta.get("purpose"), json_schema=schema_json
                )
            except Exception as exc:  # noqa: BLE001 - LLM failures must never be fatal
                last_error = f"{type(exc).__name__}: {exc}"
                extra = "\n\nYour previous attempt failed. Return only valid JSON."
                continue

            try:
                payload = json.loads(_extract_json(response.text))
                if not _matches_schema_fields(payload, schema):
                    raise ValueError(
                        "response does not contain any of the expected fields"
                    )
                value = schema.model_validate(payload)
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = f"invalid structured output: {exc}"
                extra = (
                    "\n\nYour previous output did not match the schema. "
                    f"Fix exactly these errors and return JSON only:\n{exc}"
                )
                continue

            return StructuredResult(
                value=value,
                used_llm=True,
                source="llm",
                attempts=attempt,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )

        return StructuredResult(
            value=fallback,
            used_llm=False,
            source="fallback:llm_failed",
            attempts=self.max_retries + 1,
            duration_ms=int((time.perf_counter() - started) * 1000),
            error=last_error,
        )


__all__ = ["StructuredLLM", "StructuredResult"]
