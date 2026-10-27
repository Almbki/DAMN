"""Goal-set API schemas (目标集)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.enums import GoalSetStatus
from app.schemas.goal import GoalDetailRead


class GoalSetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class GoalSetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class GoalSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str | None = None
    status: GoalSetStatus
    goal_count: int = 0
    #: Number of goals whose own status is ACTIVE (see GoalSetService).
    incomplete_goal_count: int = 0
    archived_at: datetime | None = None
    created_at: datetime


class GoalSetDetailRead(GoalSetRead):
    goals: list[GoalDetailRead] = Field(default_factory=list)


class GoalSetImpactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    goal_set_id: int = 0
    archived_goals: int = 0
    removed_tasks: int = 0
    preserved_completed_tasks: int = 0


class GoalSetRestoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    restored_goals: int = 0
    restored_tasks: int = 0


class GoalSetAttachRequest(BaseModel):
    goal_ids: list[int] = Field(min_length=1)


class GoalSetAttachRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attached_goals: int = 0


__all__ = [
    "GoalSetAttachRead",
    "GoalSetAttachRequest",
    "GoalSetCreate",
    "GoalSetDetailRead",
    "GoalSetImpactRead",
    "GoalSetRead",
    "GoalSetRestoreRead",
    "GoalSetUpdate",
]
