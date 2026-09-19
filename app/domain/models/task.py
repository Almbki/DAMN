"""Task domain entity."""

from __future__ import annotations

from datetime import date, time

from pydantic import Field

from app.domain.models.base import DomainModel
from app.domain.models.enums import CognitiveLoad, Priority, TaskStatus


class Task(DomainModel):
    id: int | None = None
    plan_id: int
    goal_id: int | None = None
    parent_task_id: int | None = None
    title: str
    description: str | None = None
    # Minutes.
    estimated_duration: int = Field(default=60, ge=1)
    predicted_duration: int | None = Field(default=None, ge=1)
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM
    priority: Priority = Priority.MEDIUM
    scheduled_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    status: TaskStatus = TaskStatus.PENDING
    # Output of the completion predictor for this task (0..1).
    completion_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    # Higher = safer to drop when the plan is overloaded (used by repair).
    is_flexible: bool = True
    order_index: int = 0
