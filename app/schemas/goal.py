"""Goal API schemas (frontend: 目标 / 待拆解清单)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.models.enums import GoalStatus, GoalType, TaskKind


class GoalDetailRead(BaseModel):
    """Goal as returned by ``/api/v1/goals``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    goal_type: str = GoalType.OTHER.value
    #: `draft` marks a not-yet-decomposed item ("待拆解").
    status: str = GoalStatus.ACTIVE.value
    deadline: date | None = None
    priority: int = 2
    estimated_minutes: int | None = None
    start_date: date | None = None
    task_kind: TaskKind | None = None
    daily_target_minutes: int | None = None
    recurrence_weekdays: list[int] | None = None
    target_amount: int | None = None
    target_unit: str | None = None
    created_at: datetime

    @field_validator("deadline", mode="before")
    @classmethod
    def _coerce_deadline(cls, value):
        """The ORM stores a datetime; the frontend expects a plain date."""
        if isinstance(value, datetime):
            return value.date()
        return value


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    goal_type: GoalType = GoalType.OTHER
    deadline: datetime | None = None
    priority: int = Field(default=2, ge=1, le=4)
    estimated_minutes: int | None = Field(default=None, ge=1)
    subject: str | None = None
    task_type: str | None = None
    #: `draft` creates a "待拆解" item; `active` a real goal.
    status: GoalStatus = GoalStatus.ACTIVE
    start_date: date | None = None
    task_kind: TaskKind | None = None
    daily_target_minutes: int | None = Field(default=None, ge=1)
    recurrence_weekdays: list[int] | None = None
    target_amount: int | None = Field(default=None, ge=0)
    target_unit: str | None = Field(default=None, max_length=64)


class GoalUpdate(BaseModel):
    """Partial update - every field is optional."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    status: GoalStatus | None = None
    deadline: datetime | None = None
    priority: int | None = Field(default=None, ge=1, le=4)
    estimated_minutes: int | None = Field(default=None, ge=1)
    subject: str | None = None
    task_type: str | None = None
    start_date: date | None = None
    task_kind: TaskKind | None = None
    daily_target_minutes: int | None = Field(default=None, ge=1)
    recurrence_weekdays: list[int] | None = None
    target_amount: int | None = Field(default=None, ge=0)
    target_unit: str | None = Field(default=None, max_length=64)


__all__ = ["GoalCreate", "GoalDetailRead", "GoalUpdate"]
