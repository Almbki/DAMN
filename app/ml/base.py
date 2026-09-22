"""Predictor interfaces (PEP 562 Protocols) and structured request/response types.

Contract rules
--------------
* The **Service** layer depends on these Protocols, never on a concrete model.
* Concrete implementations (first version: statistical / rule based mocks)
  live in ``duration_predictor.py``, ``completion_predictor.py``,
  ``stress_predictor.py`` and ``time_predictor.py``.
* Every prediction carries ``source`` so the API can be honest about whether a
  value comes from a mock, a heuristic or a trained model.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.domain.models.enums import CognitiveLoad, LoadLevel, Priority, TimeOfDay


class TaskFeatureSet(BaseModel):
    """Features derived from a :class:`~app.domain.models.task.Task`."""

    task_id: int
    title: str = ""
    task_type: str | None = None
    subject: str | None = None
    # Theory-derived (or user supplied) workload in minutes.
    estimated_duration_minutes: int = Field(ge=1)
    # 1 (easy) .. 5 (hard), optional.
    difficulty: float | None = Field(default=None, ge=1, le=5)
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM
    priority: Priority = Priority.MEDIUM
    deadline: datetime | None = None


class UserFeatureSet(BaseModel):
    """Features derived from ``TaskExecution`` + ``Feedback`` + ``UserModel``."""

    user_id: int
    # predicted = theoretical * duration_factor
    duration_factor: float = 1.0
    completion_rate_7d: float = 0.7
    completion_rate_30d: float = 0.7
    avg_stress: float = 5.0
    avg_energy: float = 5.0
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    preferred_time_slots: dict[str, str] = Field(default_factory=dict)
    # Number of execution records behind these features (confidence proxy).
    sample_size: int = 0
    execution_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class PredictionRequest(BaseModel):
    """Uniform input for every predictor."""

    task: TaskFeatureSet
    user: UserFeatureSet
    time_of_day: TimeOfDay | None = None
    available_minutes: int | None = None


class DurationPrediction(BaseModel):
    theoretical_minutes: int
    predicted_minutes: int
    factor: float
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = "mock:statistical"


class CompletionPrediction(BaseModel):
    probability: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = "mock:statistical"


class StressPrediction(BaseModel):
    predicted_stress: float = Field(ge=0.0, le=10.0)
    predicted_load_level: LoadLevel = LoadLevel.MODERATE
    should_reduce_load: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = "mock:statistical"


class TimeSlotPrediction(BaseModel):
    recommended_slot: TimeOfDay = TimeOfDay.MORNING
    alternatives: list[TimeOfDay] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = "mock:statistical"


@runtime_checkable
class DurationPredictor(Protocol):
    name: str

    def predict(self, request: PredictionRequest) -> DurationPrediction: ...


@runtime_checkable
class CompletionPredictor(Protocol):
    name: str

    def predict(self, request: PredictionRequest) -> CompletionPrediction: ...


@runtime_checkable
class StressPredictor(Protocol):
    name: str

    def predict(self, request: PredictionRequest) -> StressPrediction: ...


@runtime_checkable
class TimeSlotPredictor(Protocol):
    name: str

    def predict(self, request: PredictionRequest) -> TimeSlotPrediction: ...


# ---------------------------------------------------------------------------
# Adjustment prediction (feedback -> route)
# ---------------------------------------------------------------------------
class AdjustmentRoute(StrEnum):
    """What the system should do after a feedback cycle."""

    NO_CHANGE = "NO_CHANGE"
    MICRO_ADJUST = "MICRO_ADJUST"
    FULL_REPLAN = "FULL_REPLAN"


class AdjustmentSeverity(StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FeedbackSignal(BaseModel):
    """One recent daily feedback, as consumed by the predictors."""

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


class AdjustmentRequest(BaseModel):
    """Uniform input of the adjustment predictor."""

    user: UserFeatureSet
    progress: PlanProgress | None = None
    recent_feedback: list[FeedbackSignal] = Field(default_factory=list)
    task_features: list[TaskFeatureSet] = Field(default_factory=list)
    current_daily_load_minutes: int = 0
    available_minutes_per_day: int = 480
    user_note: str | None = None


class AdjustmentPrediction(BaseModel):
    """Structured ML decision: how far the plan should deviate.

    ``route`` values are ``NO_CHANGE`` / ``MICRO_ADJUST`` / ``FULL_REPLAN``.
    ``source`` must be truthful - ``fallback`` means no real model was used.
    """

    route: AdjustmentRoute = AdjustmentRoute.NO_CHANGE
    severity: AdjustmentSeverity = AdjustmentSeverity.NONE
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    predicted_parameters: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    recommended_action: str | None = None
    source: str = "fallback"


@runtime_checkable
class AdjustmentPredictor(Protocol):
    name: str

    def predict_adjustment(self, request: AdjustmentRequest) -> AdjustmentPrediction: ...
