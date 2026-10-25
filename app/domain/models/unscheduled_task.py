"""UnscheduledTaskRecord domain entity - a task the planner could not place.

Kept separate from CandidateSchedule so the reason survives with the plan: the
scheduler emits candidates, the service persists this snapshot, and a later
read can tell the user why a task has no slot on a given day.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow


class UnscheduledTaskRecord(DomainModel):
    id: int | None = None
    plan_id: int
    task_id: int
    date: date
    #: capacity | deadline | long_term_wait | no_slot
    reason: str = "capacity"
    created_at: datetime = Field(default_factory=utcnow)


__all__ = ["UnscheduledTaskRecord"]
