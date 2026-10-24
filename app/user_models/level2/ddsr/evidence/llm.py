"""LLM-backed evidence extraction for DDSR-V1.

The model is used strictly as a *text-to-evidence* transducer: it may copy a
verbatim span out of the user's nightly reflection and label that span with the
allowed enums.  It is never allowed to compute state values, predict tomorrow,
change trait inputs, diagnose, or invent evidence.

The raw completion is parsed with :func:`json.loads` without any pre-processing,
so markdown-fenced or otherwise decorated output is rejected.  Pydantic then
enforces ``ExtractionResult`` (``extra="forbid"``) and
:func:`validate_extraction` audits every quote and task id.
"""

from __future__ import annotations

import json
from typing import Protocol

from pydantic import ValidationError

from ..schemas import (
    CauseCategory,
    Direction,
    EvidenceType,
    ExtractionResult,
    Period,
    ReflectionField,
    ReflectionInput,
    Strength,
)
from .base import (
    EvidenceExtractionError,
    ExtractionContext,
    validate_extraction,
)


class LLMClient(Protocol):
    """Minimal synchronous text-completion contract (no network here)."""

    def complete(self, prompt: str) -> str:
        ...


class StaticLLMClient:
    """Deterministic test double.  Stores prompts, returns a fixed response."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


def _enum_values(enum_cls: type) -> str:
    return ", ".join(f'"{member.value}"' for member in enum_cls)


_REFLECTION_AREAS: tuple[tuple[ReflectionField, str], ...] = (
    (ReflectionField.DAY_REVIEW, "A. day_review -- 今天做得怎么样？"),
    (ReflectionField.STUCK_POINTS, "B. stuck_points -- 哪里卡住了？"),
    (ReflectionField.STATE_REVIEW, "C. state_review -- 今天状态怎么样？"),
    (ReflectionField.TOMORROW_OUTLOOK, "D. tomorrow_outlook -- 明天怎么看？"),
)


class LLMEvidenceExtractor:
    """Extract auditable evidence items from reflection text via an LLM client."""

    name = "llm_evidence_extractor"
    version = "1.0"

    def __init__(
        self,
        client: LLMClient,
        name: str | None = None,
        version: str | None = None,
    ) -> None:
        self.client = client
        if name is not None:
            self.name = name
        if version is not None:
            self.version = version

    def extract(
        self, reflection: ReflectionInput, context: ExtractionContext
    ) -> ExtractionResult:
        prompt = self._build_prompt(reflection, context)
        raw = self.client.complete(prompt)

        if not isinstance(raw, str):
            raise EvidenceExtractionError(
                f"{self.name} expected the LLM client to return str, "
                f"got {type(raw).__name__}"
            )

        # Strict JSON only: no fence stripping, no repair, no extraction of the
        # first object inside surrounding prose.
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EvidenceExtractionError(
                f"{self.name} returned invalid JSON (fences/extra text are not "
                f"allowed): {exc.msg} at line {exc.lineno} column {exc.colno}"
            ) from exc

        # ``ExtractionResult`` forbids extra keys, so ``state_value``,
        # ``prediction``, ``diagnosis``, etc. are rejected here.
        try:
            result = ExtractionResult.model_validate(payload)
        except ValidationError as exc:
            raise EvidenceExtractionError(
                f"{self.name} returned a payload that violates the "
                f"ExtractionResult schema: {exc}"
            ) from exc

        return validate_extraction(result, reflection, context)

    def _build_prompt(
        self, reflection: ReflectionInput, context: ExtractionContext
    ) -> str:
        areas = []
        for field, label in _REFLECTION_AREAS:
            text = reflection.text_for(field)
            rendered = text if text else "(not provided)"
            areas.append(
                f'{label}\n   source_field = "{field.value}"\n   text: {rendered}'
            )
        areas_block = "\n\n".join(areas)

        known_ids = sorted(context.known_task_ids)
        known_ids_block = (
            json.dumps(known_ids, ensure_ascii=False) if known_ids else "(none)"
        )

        schema = json.dumps(
            ExtractionResult.model_json_schema(),
            ensure_ascii=False,
            indent=2,
        )

        return f"""You are a strict, non-inferential evidence annotator for a daily
self-regulation study. You copy short, verbatim spans of the user's nightly
reflection and label each span with the allowed categories below.

HARD PROHIBITIONS -- never violate any of them:
- Do NOT compute, estimate, infer, or output any state value (no fatigue,
  stress, or self-efficacy scores, probabilities, or numbers of any kind).
- Do NOT predict tomorrow or extrapolate future behaviour or outcomes.
- Do NOT modify, infer, or restate personality traits.
- Do NOT diagnose the user, name a disorder, or use clinical labels.
- Do NOT invent evidence. Every item must be backed by an exact quote.
- Omit anything that is not explicitly stated. When in doubt, emit no item;
  an empty "evidence" list is a correct and preferred answer.

VERBATIM QUOTE RULE:
- "evidence_text" MUST be an exact substring of the reflection area named by
  "source_field". Copy the characters as written: no paraphrase, no ellipsis,
  no translation, no added or removed punctuation, no trimming of words.
- A quote must be at least {context.min_quote_chars} characters long.
- The quote may come only from the four source areas listed below.
- If you cannot quote it, you must not report it.

SOURCE AREAS (the only permissible "source_field" values):
{areas_block}

KNOWN TASK IDS (the only permissible "task_id" values):
{known_ids_block}
- Set "task_id" only when the reflection explicitly refers to that task id.
  Otherwise use null. Never guess or map a task title to an id.

ALLOWED ENUM VALUES:
- evidence_type: {_enum_values(EvidenceType)}
- direction: {_enum_values(Direction)}
- strength: {_enum_values(Strength)}
- period: {_enum_values(Period)}
- cause_category: {_enum_values(CauseCategory)} (or null)
- source_field: {_enum_values(ReflectionField)}
- voluntary: true, false, or null
- task_id: one of the known task ids above, or null

SEMANTIC RULES:
- fatigue / stress / self_efficacy evidence MUST set "voluntary" to null.
- Area D (tomorrow_outlook) may only yield "self_efficacy" evidence about the
  user's confidence/capability for tomorrow. Do NOT extract fatigue, stress,
  procrastination, or interruption from area D; those describe today, not a
  forecast. A predicted "tomorrow meeting" is not today's interruption.
- procrastination evidence MUST use "direction": "increase",
  "voluntary": true, and a cause that is not one of
  external_interruption, illness, task_difficulty, plan_change.
- interruption evidence MUST use "direction": "increase" and
  "voluntary": false (or null).

OUTPUT FORMAT:
Return exactly one JSON object and nothing else -- no markdown, no code fences,
no commentary before or after it. It must validate against this JSON Schema and
extra properties are forbidden:

{schema}
"""
