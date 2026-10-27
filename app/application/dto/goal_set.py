"""Application DTOs for goal sets (目标集)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models import Goal
from app.domain.models.enums import GoalSetStatus


class GoalSetSummary(BaseModel):
    """List/card view of a goal set."""

    id: int
    user_id: int
    name: str
    description: str | None = None
    status: GoalSetStatus
    #: Every goal attached to the set (including archived / cancelled ones).
    goal_count: int = 0
    #: Goals whose status is ACTIVE. This is the "still being worked on" count.
    incomplete_goal_count: int = 0
    archived_at: datetime | None = None
    created_at: datetime


class GoalSetDetail(GoalSetSummary):
    """Summary plus every goal in the set."""

    goals: list[Goal] = Field(default_factory=list)


class GoalSetImpact(BaseModel):
    """Effect of archiving a whole set."""

    goal_set_id: int = 0
    archived_goals: int = 0
    removed_tasks: int = 0
    preserved_completed_tasks: int = 0


class GoalSetRestoreResult(BaseModel):
    """Effect of restoring a whole set."""

    restored_goals: int = 0
    restored_tasks: int = 0


class GoalAttachResult(BaseModel):
    """Number of goals newly attached to a set."""

    attached_goals: int = 0


__all__ = [
    "GoalAttachResult",
    "GoalSetDetail",
    "GoalSetImpact",
    "GoalSetRestoreResult",
    "GoalSetSummary",
]
