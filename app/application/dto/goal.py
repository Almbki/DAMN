"""Application DTO for goal creation (no API-schema dependency)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.domain.models.enums import GoalStatus, GoalType, TaskKind


@dataclass(frozen=True, slots=True)
class GoalCreateData:
    title: str
    description: str | None = None
    goal_type: GoalType = GoalType.OTHER
    deadline: datetime | None = None
    priority: int = 2
    estimated_minutes: int | None = None
    subject: str | None = None
    task_type: str | None = None
    status: GoalStatus = GoalStatus.ACTIVE
    start_date: date | None = None
    task_kind: TaskKind | None = None
    daily_target_minutes: int | None = None
    recurrence_weekdays: list[int] | None = None
    target_amount: int | None = None
    target_unit: str | None = None


__all__ = ["GoalCreateData"]