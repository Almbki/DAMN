"""Typed contracts shared by the user-model runtime and the application layer.

Rules
-----
* No raw ``dict`` crosses the runtime boundary for model input/output.
* Every snapshot carries :class:`ModelMetadata` (version + artifact hash).
* A missing value is ``None`` / ``ModelStatus.UNAVAILABLE`` - never a
  fabricated number.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Level3Mode(StrEnum):
    """How Level 3 participates in a planning run."""

    OFF = "off"
    SHADOW = "shadow"
    #: Reserved. Not opened for production control in this version.
    ACTIVE = "active"


class ModelLevel(StrEnum):
    LEVEL1 = "level1"
    LEVEL2 = "level2"
    LEVEL3 = "level3"


class ModelStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    NOT_FITTED = "not_fitted"


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactInfo(_Contract):
    """Identity of one loaded artifact bundle."""

    path: str
    sha256: str
    version: str


class ModelMetadata(_Contract):
    level: ModelLevel
    model_version: str
    artifact_version: str
    artifact_hash: str
    feature_version: str
    mode: Level3Mode | None = None
    status: ModelStatus = ModelStatus.OK
    degraded_reason: str | None = None


class TraitDomain(_Contract):
    theta: float
    se: float
    ci95: tuple[float, float] | None = None
    items_answered: int = 0


class TraitSnapshot(_Contract):
    """Level 1 output (stable traits), read-only for every later layer."""

    model_version: str
    schema_version: str = "1.0"
    domains: dict[str, TraitDomain]
    calibration: dict[str, Any] = Field(default_factory=dict)
    metadata: ModelMetadata


class StateEstimate(_Contract):
    value: float
    uncertainty: float
    evidence_availability: str = "none"
    evidence_count: int = 0
    conflict: bool = False


class DynamicStateSnapshot(_Contract):
    """Level 2 output (pre-task daily state S_d^-)."""

    date: date
    fatigue: StateEstimate
    stress: StateEstimate
    self_efficacy: StateEstimate
    next_day_prior: dict[str, float] = Field(default_factory=dict)
    next_day_uncertainty: dict[str, float] = Field(default_factory=dict)
    model_version: str
    config_version: str
    cold_start: bool = False
    gap_days: int = 0
    #: Full auditable Level 2 profile (no prompt bodies, no raw free text).
    profile_json: dict[str, Any] = Field(default_factory=dict)
    metadata: ModelMetadata


class HistoryBundle(_Contract):
    """Real execution history used by Level 3 (never future data)."""

    completion_history: list[bool] = Field(default_factory=list)
    duration_ratio_history: list[float] = Field(default_factory=list)
    similar_duration_ratio_history: list[float] = Field(default_factory=list)
    total_historical_tasks: int = 0
    completed_task_count: int = 0
    failed_task_count: int = 0
    usable_duration_samples: int = 0
    similar_task_sample_count: int = 0
    similar_task_type: str | None = None
    recent_goal_attainment: float | None = None


class TaskPredictionContext(_Contract):
    """Task/context inputs for one Level 3 prediction."""

    task_id: str
    title: str = ""
    estimated_duration_minutes: float = Field(gt=0)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    deadline: datetime | None = None
    planned_start: datetime | None = None
    task_type: str | None = None
    available_time_minutes: float | None = None
    time_of_day: int = Field(default=0, ge=0, le=23)


class UserModelContext(_Contract):
    """The only user-model shape the agent/application passes around."""

    trait: TraitSnapshot | None = None
    state: DynamicStateSnapshot | None = None
    history: HistoryBundle | None = None
    metadata: tuple[ModelMetadata, ...] = ()
    degraded: bool = False
    degraded_reasons: tuple[str, ...] = ()
    level3_mode: Level3Mode = Level3Mode.SHADOW


class Level3Prediction(_Contract):
    """Level 3 output.

    ``predicted_duration_minutes`` is always present (cold start falls back to
    the task's own estimate). ``completion_probability`` is ``None`` when the
    model has insufficient real history - it is never fabricated.
    """

    completion_probability: float | None = None
    completion_uncertainty: float | None = None
    completion_interval: tuple[float, float] | None = None
    predicted_duration_minutes: float | None = None
    duration_uncertainty: float | None = None
    duration_interval: tuple[float, float] | None = None
    prediction_mode: str = "cold_start"
    prediction_status: str = "insufficient_behavior_data"
    model_version: str = ""
    feature_snapshot_id: str = ""
    data_support: dict[str, Any] = Field(default_factory=dict)
    source_level1_version: str = ""
    source_level2_version: str = ""
    reasons: tuple[str, ...] = ()
    degraded: bool = False


__all__ = [
    "ArtifactInfo",
    "DynamicStateSnapshot",
    "HistoryBundle",
    "Level3Mode",
    "Level3Prediction",
    "ModelLevel",
    "ModelMetadata",
    "ModelStatus",
    "StateEstimate",
    "TaskPredictionContext",
    "TraitDomain",
    "TraitSnapshot",
    "UserModelContext",
]