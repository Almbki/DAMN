"""Goal API schemas (frontend: 目标 / 待拆解清单)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.enums import GoalStatus, GoalType


class GoalDetailRead(BaseModel):
    """Goal as returned by ``/api/v1/goals``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    goal_type: str = GoalType.OTHER.value
    #: `draft` marks a not-yet-decomposed item ("待拆解").
    status: str = GoalStatus.ACTIVE.value
    deadline: datetime | None = None
    priority: int = 2
    estimated_minutes: int | None = None
    created_at: datetime


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    goal_type: GoalType = GoalType.OTHER
    deadline: datetime | None = None
    priority: int = Field(default=2, ge=1, le=4)
    estimated_minutes: int | None = Field(default=None, ge=1)
    subject: str | None = None
    task_type: str | None = None
    #: `draft` creates a "待拆解" item; `active` a real goal.
    status: GoalStatus = GoalStatus.ACTIVE


class GoalUpdate(BaseModel):
    """Partial update - every field is optional."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: GoalStatus | None = None
    deadline: datetime | None = None
    priority: int | None = Field(default=None, ge=1, le=4)
    estimated_minutes: int | None = Field(default=None, ge=1)
    subject: str | None = None
    task_type: str | None = None


__all__ = ["GoalCreate", "GoalDetailRead", "GoalUpdate"]
