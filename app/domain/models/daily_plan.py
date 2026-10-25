"""DailyPlanRecord domain entity - one persisted day of a plan.

The scheduler's DailyPlan value object is a pure in-memory report; this entity
is the persistence snapshot written to daily_plans (capacity, usage, task ids
and the human-readable reasons) so a later read can explain an old plan.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow


class DailyPlanRecord(DomainModel):
    id: int | None = None
    plan_id: int
    date: date
    capacity_minutes: int = Field(default=0, ge=0)
    used_minutes: int = Field(default=0, ge=0)
    #: Task ids placed on this day (the ORM column is named tasks).
    tasks: list[int] = Field(default_factory=list)
    #: Rationale/audit strings produced by the scheduler.
    reasons: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


__all__ = ["DailyPlanRecord"]
