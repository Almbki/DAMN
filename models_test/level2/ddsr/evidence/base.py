"""Replaceable evidence-extraction contract.

An extractor may read only the reflection text.  It returns ``EvidenceItem``
objects; it must never compute state values, predict tomorrow, modify traits,
or produce a diagnosis.  Every item is audited against the source text.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ..schemas import ExtractionResult, ReflectionInput


class EvidenceExtractionError(ValueError):
    """Raised when an extractor output is invalid or not auditable."""


@dataclass(frozen=True)
class ExtractionContext:
    known_task_ids: frozenset[str]
    date: date
    min_quote_chars: int = 2


class EvidenceExtractor(Protocol):
    name: str
    version: str

    def extract(
        self, reflection: ReflectionInput, context: ExtractionContext
    ) -> ExtractionResult:
        ...


def validate_extraction(
    result: ExtractionResult,
    reflection: ReflectionInput,
    context: ExtractionContext,
) -> ExtractionResult:
    """Audit every evidence item against the original reflection field.

    The validation is intentionally strict: hallucinated quotes, unknown task
    ids, and too-short spans reject the extraction instead of silently
    contributing evidence.
    """
    for index, item in enumerate(result.evidence):
        source = reflection.text_for(item.source_field)
        if not source:
            raise EvidenceExtractionError(
                f"evidence[{index}] references empty reflection field "
                f"{item.source_field.value!r}"
            )
        quote = item.evidence_text
        if quote not in source and quote.strip() not in source:
            raise EvidenceExtractionError(
                f"evidence[{index}] quote is not a verbatim substring of "
                f"{item.source_field.value!r}"
            )
        if len(quote.strip()) < context.min_quote_chars:
            raise EvidenceExtractionError(
                f"evidence[{index}] quote is shorter than "
                f"{context.min_quote_chars} characters"
            )
        if item.task_id is not None and item.task_id not in context.known_task_ids:
            raise EvidenceExtractionError(
                f"evidence[{index}] references unknown task_id {item.task_id!r}"
            )
    return result
