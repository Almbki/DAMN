"""Task API schemas."""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.enums import CognitiveLoad, Priority, TaskStatus


class TaskStandardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    estimated_duration: int
    completed: bool
    order_index: int


class TaskStandardUpdate(BaseModel):
    id: int
    completed: bool


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    goal_id: int | None = None
    parent_task_id: int | None = None
    title: str
    description: str | None = None
    estimated_duration: int
    predicted_duration: int | None = None
    cognitive_load: CognitiveLoad
    priority: Priority
    scheduled_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    status: TaskStatus
    completion_probability: float | None = None
    is_flexible: bool = True
    order_index: int = 0
    standards: list[TaskStandardRead] = Field(default_factory=list)


class TaskUpdateRequest(BaseModel):
    """Patch payload for a single task (all fields optional)."""

    status: TaskStatus | None = None
    completed: bool | None = None
    actual_duration: int | None = Field(default=None, ge=0)
    difficulty_feedback: int | None = Field(default=None, ge=1, le=5)
    stress_before: int | None = Field(default=None, ge=0, le=10)
    stress_after: int | None = Field(default=None, ge=0, le=10)
    failure_reason: str | None = Field(default=None, max_length=500)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    standard_updates: list[TaskStandardUpdate] | None = None
