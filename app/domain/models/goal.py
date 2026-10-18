"""Goal domain entity (long-term / short-term objectives with deadlines)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow
from app.domain.models.enums import GoalStatus, GoalType, Priority, TaskKind


class Goal(DomainModel):
    id: int | None = None
    user_id: int
    title: str
    description: str | None = None
    goal_type: GoalType = GoalType.SHORT_TERM
    deadline: datetime | None = None
    priority: Priority = Priority.MEDIUM
    status: GoalStatus = GoalStatus.ACTIVE
    # Estimated duration in minutes supplied by the user (optional).
    estimated_minutes: int | None = None
    # Optional first day of a long-term/routine goal (defaults to plan start).
    start_date: date | None = None
    # ``None`` means "infer from goal_type" (LONG_TERM -> long_term, etc.).
    task_kind: TaskKind | None = None
    # Daily quota for a split goal (long-term/routine). Optional.
    daily_target_minutes: int | None = None
    # 0=Mon..6=Sun. None/empty means every day.
    recurrence_weekdays: list[int] | None = None
    # Optional measurable target copied onto each occurrence.
    target_amount: int | None = None
    target_unit: str | None = None
    # Free-form options from the client (subject, task type, ...).
    options: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
