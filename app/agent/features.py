"""Typed agent-side feature contracts (no model implementation lives here).

These replace the former ``app.ml.base`` contracts for *context* data. The
concrete three-layer models live in ``app.user_models``; nothing here predicts
anything.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domain.models.enums import CognitiveLoad, Priority


class TaskFeatureSet(BaseModel):
    """Features derived from a task/draft for deterministic estimation."""

    task_id: int
    title: str = ""
    task_type: str | None = None
    subject: str | None = None
    estimated_duration_minutes: int = Field(ge=1)
    difficulty: float | None = Field(default=None, ge=1, le=5)
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM
    priority: Priority = Priority.MEDIUM
    deadline: datetime | None = None


class UserFeatureSet(BaseModel):
    """Observed user aggregates (not a model prediction).

    ``avg_stress`` / ``avg_energy`` are 0..10 projections of the Level 2 state
    (``stress`` and ``1 - fatigue``) for prompt/display compatibility. The
    authoritative values are the typed Level 1/2 snapshots.
    """

    user_id: int
    completion_rate_7d: float | None = None
    completion_rate_30d: float | None = None
    avg_stress: float | None = Field(default=None, ge=0, le=10)
    avg_energy: float | None = Field(default=None, ge=0, le=10)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    preferred_time_slots: dict[str, str] = Field(default_factory=dict)
    sample_size: int = 0
    execution_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class FeedbackSignal(BaseModel):
    """One recent daily check-in."""

    date: date
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    stress_level: int | None = Field(default=None, ge=0, le=10)
    energy_level: int | None = Field(default=None, ge=0, le=10)
    delay_reason: str | None = None


class PlanProgress(BaseModel):
    """Execution progress of the current plan version."""

    plan_id: int | None = None
    version: int = 1
    total_tasks: int = 0
    completed_tasks: int = 0
    skipped_tasks: int = 0
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    days_elapsed: int = 0
    days_remaining: int = 0


__all__ = [
    "FeedbackSignal",
    "PlanProgress",
    "TaskFeatureSet",
    "UserFeatureSet",
]