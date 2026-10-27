"""Task API schemas."""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.enums import CognitiveLoad, Priority, TaskKind, TaskStatus


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
    #: Truthful provenance of the production numbers. Never "shadow".
    prediction_source: str | None = None
    prediction_mode: str | None = None
    #: Active execution started_at (from the latest unfinished TaskExecution).
    started_at: datetime | None = None
    is_flexible: bool = True
    task_kind: TaskKind = TaskKind.ONE_OFF
    series_id: str | None = None
    series_index: int | None = None
    occurrence_date: date | None = None
    target_amount: int | None = None
    target_unit: str | None = None
    #: Cross-version semantic work-unit identity.
    work_unit_key: str | None = None
    #: Execution chunk order inside its work unit (None for non-chunk tasks).
    chunk_index: int | None = None
    #: Final deterministic scheduling failure (only for unscheduled tasks).
    scheduling_reason: str | None = None
    scheduling_detail: str | None = None
    order_index: int = 0
    #: Read-time aggregation across this task's chunk group.
    chunk_count: int = 1
    completed_chunks: int = 0
    work_unit_completed: bool = False
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
    #: Partial completion (0..1) for a task that is not fully done.
    completion_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    #: Optional observed interruption count; null means not observed.
    interruption_count: int | None = Field(default=None, ge=0)
    # Editable / reschedulable fields (explicit user overrides).
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    estimated_duration: int | None = Field(default=None, ge=1)
    priority: Priority | None = None
    cognitive_load: CognitiveLoad | None = None
    scheduled_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    standard_updates: list[TaskStandardUpdate] | None = None
