"""TaskExecution domain entity.

This is the most important ML data asset of the system: every real execution
records planned vs actual duration, completion, stress before/after and the
context needed to train the Duration / Completion / Stress predictors.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow
from app.domain.models.enums import TimeOfDay


class TaskExecution(DomainModel):
    id: int | None = None
    task_id: int
    user_id: int
    # Minutes.
    planned_duration: int = Field(ge=0)
    actual_duration: int | None = Field(default=None, ge=0)
    # 0..1
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    # 1..5 self report: 1 = much easier than expected, 5 = much harder.
    difficulty_feedback: int | None = Field(default=None, ge=1, le=5)
    stress_before: int | None = Field(default=None, ge=0, le=10)
    stress_after: int | None = Field(default=None, ge=0, le=10)
    failure_reason: str | None = None
    time_of_day: TimeOfDay | None = None
    completed: bool = False
    created_at: datetime = Field(default_factory=utcnow)
