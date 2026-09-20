"""Goal domain entity (long-term / short-term objectives with deadlines)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow
from app.domain.models.enums import GoalStatus, GoalType, Priority


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
    # Free-form options from the client (subject, task type, ...).
    options: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
