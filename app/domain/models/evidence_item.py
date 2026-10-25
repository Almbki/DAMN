"""EvidenceItem domain entity (reflection evidence for Level 2)."""

from __future__ import annotations

from datetime import datetime

from app.domain.models.base import DomainModel, utcnow


class EvidenceItem(DomainModel):
    id: int | None = None
    user_id: int
    feedback_id: int | None = None
    task_id: int | None = None
    #: day_review / stuck_points / state_review / tomorrow_outlook
    reflection_field: str
    #: fatigue / stress / self_efficacy / procrastination / interruption
    evidence_type: str
    #: increase / decrease
    direction: str
    #: weak / moderate / strong
    strength: str
    period: str
    cause_category: str | None = None
    voluntary: bool | None = None
    #: Must be a verbatim substring of the reflection text.
    evidence_text: str
    #: llm / rule
    extractor: str
    extractor_version: str
    #: accepted / rejected
    status: str
    created_at: datetime = utcnow()


__all__ = ["EvidenceItem"]
