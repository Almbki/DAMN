"""Level 3 schemas for prediction input/output/snapshots."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

PredictionMode = Literal["cold_start", "history_baseline", "learned_model"]
PredictionStatus = Literal["ok", "insufficient_behavior_data", "insufficient_labels", "gate_failed", "missing_data"]


@dataclass
class TraitInput:
    # Only read from Level 1 TraitProfile V1
    theta_n: float
    theta_e: float
    theta_o: float
    theta_a: float
    theta_c: float
    se_n: float
    se_e: float
    se_o: float
    se_a: float
    se_c: float
    model_version: str = "trait_v1"
    schema_version: str = "1.0"
    calibration_model: str | None = None
    calibration_version: str | None = None


@dataclass
class StateInput:
    # Only pre-task state S_d^- from Level 2
    fatigue: float
    fatigue_uncertainty: float
    stress: float
    stress_uncertainty: float
    self_efficacy: float
    self_efficacy_uncertainty: float
    model_version: str = "ddsr_v1"
    schema_version: str = "1.0"


@dataclass
class TaskInput:
    task_id: str
    estimated_duration_minutes: float
    difficulty: int | None = None
    deadline: datetime | None = None
    planned_start: datetime | None = None
    task_type: str | None = None

    @property
    def hours_to_deadline(self) -> float | None:
        if self.deadline is None:
            return None
        # requires prediction_timestamp set externally
        return None

    @property
    def has_planned_start(self) -> bool:
        return self.planned_start is not None


@dataclass
class ContextInput:
    prediction_timestamp: datetime
    time_of_day: int  # hour
    available_time_minutes: float | None = None


@dataclass
class HistorySupport:
    total_historical_tasks: int = 0
    completed_task_count: int = 0
    failed_task_count: int = 0
    usable_duration_samples: int = 0
    similar_task_sample_count: int = 0
    similar_task_type: str | None = None


@dataclass
class HistoryInput:
    completion_history: list[bool] = field(default_factory=list)
    duration_ratio_history: list[float] = field(default_factory=list)  # actual/estimated
    similar_duration_ratio_history: list[float] = field(default_factory=list)
    recent_goal_attainment: float | None = None
    support: HistorySupport = field(default_factory=HistorySupport)


@dataclass
class Level3PredictionInput:
    trait: TraitInput
    state: StateInput  # pre-task only
    task: TaskInput
    context: ContextInput
    history: HistoryInput


@dataclass
class PredictionSnapshot:
    snapshot_id: str
    prediction_timestamp: datetime
    trait: TraitInput
    state: StateInput  # frozen pre-task state
    task: TaskInput
    context: ContextInput
    history: HistoryInput
    feature_snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutcomeRecord:
    task_id: str
    completed: bool
    completion_ratio: float | None = None
    actual_duration_minutes: float | None = None
    outcome_timestamp: datetime | None = None
    notes: str | None = None


@dataclass
class Level3PredictionResult:
    completion_probability: float | None
    completion_uncertainty: float | None
    completion_interval: tuple[float, float] | None
    predicted_duration_minutes: float
    duration_uncertainty: float | None
    duration_interval: tuple[float, float] | None
    prediction_mode: PredictionMode
    prediction_status: PredictionStatus
    model_version: str
    prediction_timestamp: datetime
    data_support: HistorySupport
    feature_snapshot_id: str
    source_level1_version: str
    source_level2_version: str
    reasons: list[str] = field(default_factory=list)
    feature_vector: dict[str, Any] = field(default_factory=dict)
