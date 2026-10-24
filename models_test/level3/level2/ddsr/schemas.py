"""DDSR-V1 schemas: task logs, nightly reflection, evidence, and daily profile.

The schemas are deliberately strict (``extra="forbid"``) because the LLM
evidence extractor must not be able to smuggle state values, diagnoses, or
future predictions into the pipeline.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class StateName(StrEnum):
    FATIGUE = "fatigue"
    STRESS = "stress"
    SELF_EFFICACY = "self_efficacy"


STATE_NAMES: tuple[StateName, ...] = (
    StateName.FATIGUE,
    StateName.STRESS,
    StateName.SELF_EFFICACY,
)


class EvidenceType(StrEnum):
    FATIGUE = "fatigue"
    STRESS = "stress"
    SELF_EFFICACY = "self_efficacy"
    PROCRASTINATION = "procrastination"
    INTERRUPTION = "interruption"


STATE_EVIDENCE_TYPES: frozenset[EvidenceType] = frozenset(
    {
        EvidenceType.FATIGUE,
        EvidenceType.STRESS,
        EvidenceType.SELF_EFFICACY,
    }
)

EVIDENCE_TO_STATE: dict[EvidenceType, StateName] = {
    EvidenceType.FATIGUE: StateName.FATIGUE,
    EvidenceType.STRESS: StateName.STRESS,
    EvidenceType.SELF_EFFICACY: StateName.SELF_EFFICACY,
}


class Direction(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"


class Strength(StrEnum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class Period(StrEnum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    UNSPECIFIED = "unspecified"


class ReflectionField(StrEnum):
    """The four nightly reflection areas A-D from the product contract."""

    DAY_REVIEW = "day_review"  # A. 今天做得怎么样？
    STUCK_POINTS = "stuck_points"  # B. 哪里卡住了？
    STATE_REVIEW = "state_review"  # C. 今天状态怎么样？
    TOMORROW_OUTLOOK = "tomorrow_outlook"  # D. 明天怎么看？


class InputModality(StrEnum):
    TEXT = "text"
    VOICE_TRANSCRIPT = "voice_transcript"


class CauseCategory(StrEnum):
    """Reason categories, aligned with Loeffler et al. (2019) and related work.

    The categories are descriptive only; they are never treated as a
    personality label or a direct state value.
    """

    UNREALISTIC_PLANNING = "unrealistic_planning"
    DISTRACTION = "distraction"
    ATTRACTIVE_ALTERNATIVE = "attractive_alternative"
    MOTIVATION_VOLITION = "motivation_volition"
    TIME_PRESSURE = "time_pressure"
    EMOTION_REGULATION = "emotion_regulation"
    NERVOUSNESS = "nervousness"
    FATIGUE = "fatigue"
    ANXIETY_SELF_DOUBT = "anxiety_self_doubt"
    EXTERNAL_INTERRUPTION = "external_interruption"
    ILLNESS = "illness"
    TASK_DIFFICULTY = "task_difficulty"
    PLAN_CHANGE = "plan_change"
    AVOIDANCE = "avoidance"
    OTHER = "other"


#: Causes that explicitly must NOT be converted into procrastination evidence.
EXTERNAL_CAUSES: frozenset[CauseCategory] = frozenset(
    {
        CauseCategory.EXTERNAL_INTERRUPTION,
        CauseCategory.ILLNESS,
        CauseCategory.TASK_DIFFICULTY,
        CauseCategory.PLAN_CHANGE,
    }
)


class EvidenceItem(StrictModel):
    """One auditable evidence span extracted from a reflection field.

    ``evidence_text`` must be a verbatim substring of the source reflection
    field.  The item is not a state value and carries no diagnosis.
    """

    evidence_type: EvidenceType
    direction: Direction
    strength: Strength = Strength.MODERATE
    period: Period = Period.UNSPECIFIED
    task_id: str | None = None
    cause_category: CauseCategory | None = None
    voluntary: bool | None = None
    evidence_text: str = Field(min_length=1, max_length=500)
    source_field: ReflectionField

    @model_validator(mode="after")
    def _semantic_guards(self) -> EvidenceItem:
        if self.evidence_type is EvidenceType.PROCRASTINATION:
            if self.voluntary is not True:
                raise ValueError(
                    "procrastination evidence requires voluntary=True; "
                    "external interruption or plan change is not procrastination"
                )
            if self.cause_category in EXTERNAL_CAUSES:
                raise ValueError("external cause cannot be procrastination evidence")
            if self.direction is not Direction.INCREASE:
                raise ValueError("procrastination evidence must use direction=increase")
        if self.evidence_type is EvidenceType.INTERRUPTION:
            if self.voluntary is True:
                raise ValueError("interruption evidence cannot be voluntary")
            if self.direction is not Direction.INCREASE:
                raise ValueError("interruption evidence must use direction=increase")
        if self.evidence_type in STATE_EVIDENCE_TYPES and self.voluntary is not None:
            raise ValueError("state evidence must not set voluntary")
        return self

    @property
    def target_state(self) -> StateName | None:
        return EVIDENCE_TO_STATE.get(self.evidence_type)


class ReflectionInput(StrictModel):
    """Four optional free-text / voice-transcript areas, never a questionnaire."""

    day_review: str | None = None
    stuck_points: str | None = None
    state_review: str | None = None
    tomorrow_outlook: str | None = None
    input_modality: dict[ReflectionField, InputModality] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _strip(cls, data):
        # ``validate_assignment=True`` is inherited from StrictModel; stripping
        # in a ``mode="after"`` validator with setattr would re-enter validation
        # recursively. Normalize the incoming payload instead.
        if isinstance(data, dict):
            cleaned = dict(data)
            for field in ReflectionField:
                value = cleaned.get(field.value)
                if isinstance(value, str):
                    cleaned[field.value] = value.strip() or None
            return cleaned
        return data

    def text_for(self, field: ReflectionField) -> str:
        value = getattr(self, field.value)
        return value or ""

    def present_fields(self) -> list[ReflectionField]:
        return [field for field in ReflectionField if self.text_for(field)]

    def is_empty(self) -> bool:
        return not self.present_fields()


class ExtractionResult(StrictModel):
    """The only object an LLM is allowed to return."""

    evidence: list[EvidenceItem] = Field(default_factory=list)


class TaskPlan(StrictModel):
    task_id: str = Field(min_length=1)
    title: str | None = None
    planned_start: datetime
    estimated_duration_minutes: int = Field(gt=0)
    deadline: datetime | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def _deadline_not_before_start(self) -> TaskPlan:
        if self.deadline is not None and self.deadline < self.planned_start:
            raise ValueError("deadline must not be before planned_start")
        return self


class TaskExecution(StrictModel):
    task_id: str = Field(min_length=1)
    actual_start: datetime | None = None
    actual_duration_minutes: float | None = Field(default=None, ge=0)
    completion_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    completed: bool = False
    interruption_count: int = Field(default=0, ge=0)


class PassiveContext(StrictModel):
    """Reserved, uniform passive-context interface.

    DDSR-V1 never interprets these fields.  They are stored only for a future
    module and must not be read as low self-control, procrastination, or fatigue.
    """

    screen_time_minutes: float | None = Field(default=None, ge=0)
    unlock_count: int | None = Field(default=None, ge=0)
    late_night_usage_minutes: float | None = Field(default=None, ge=0)
    app_switching_count: int | None = Field(default=None, ge=0)
    sleep_duration_minutes: float | None = Field(default=None, ge=0)
    sleep_quality: float | None = Field(default=None, ge=0.0, le=1.0)

    def is_available(self) -> bool:
        return any(
            getattr(self, name) is not None
            for name in (
                "screen_time_minutes",
                "unlock_count",
                "late_night_usage_minutes",
                "app_switching_count",
                "sleep_duration_minutes",
                "sleep_quality",
            )
        )


class DayInput(StrictModel):
    date: date
    task_plans: list[TaskPlan] = Field(default_factory=list)
    task_executions: list[TaskExecution] = Field(default_factory=list)
    reflection: ReflectionInput | None = None
    passive_context: PassiveContext | None = None

    @model_validator(mode="after")
    def _unique_ids(self) -> DayInput:
        plan_ids = [plan.task_id for plan in self.task_plans]
        if len(plan_ids) != len(set(plan_ids)):
            raise ValueError("task_plans must have unique task_id values")
        exec_ids = [execution.task_id for execution in self.task_executions]
        if len(exec_ids) != len(set(exec_ids)):
            raise ValueError("task_executions must have unique task_id values")
        unknown = set(exec_ids) - set(plan_ids)
        if unknown:
            raise ValueError(f"task_executions reference unknown task ids: {sorted(unknown)}")
        return self


# ---------------------------------------------------------------------------
# Derived behavioral indicators
# ---------------------------------------------------------------------------


class TaskDerived(StrictModel):
    task_id: str
    started: bool
    start_delay_minutes: float | None
    duration_ratio: float | None
    completion_ratio: float | None
    completed: bool
    interruption_count: int
    late_start_candidate: bool
    evidence_available: bool


class InitiationIndicator(StrictModel):
    tasks_planned: int
    tasks_with_log: int
    tasks_started: int
    on_time_tasks: int
    mean_start_delay_minutes: float | None
    start_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    planned_coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_available: bool


class PersistenceIndicator(StrictModel):
    tasks_started: int
    mean_duration_ratio: float | None
    total_actual_duration_minutes: float
    total_estimated_duration_minutes: float
    interruption_count: int
    continuation_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_available: bool


class GoalAttainmentIndicator(StrictModel):
    value: float | None = Field(default=None, ge=0.0, le=1.0)
    tasks_planned: int
    tasks_logged: int
    tasks_completed: int
    evidence_available: bool


class ProcrastinationEvidenceIndicator(StrictModel):
    confirmed: list[EvidenceItem] = Field(default_factory=list)
    candidate_task_ids: list[str] = Field(default_factory=list)
    late_start_candidate_count: int = 0
    evidence_available: bool = False
    note: str = (
        "A late start is only a candidate. It is not procrastination unless the "
        "user explicitly reports voluntary delay/avoidance."
    )


class BehavioralIndicators(StrictModel):
    initiation: InitiationIndicator
    persistence: PersistenceIndicator
    goal_attainment: GoalAttainmentIndicator
    procrastination_evidence: ProcrastinationEvidenceIndicator


# ---------------------------------------------------------------------------
# Daily dynamic-state profile
# ---------------------------------------------------------------------------


class EvidenceAvailability(StrEnum):
    NONE = "none"
    REFLECTION_ONLY = "reflection_only"
    TASK_LOG_ONLY = "task_log_only"
    REFLECTION_AND_TASK_LOG = "reflection_and_task_log"


class StateEstimate(StrictModel):
    observed_on: date
    prior: float = Field(ge=0.0, le=1.0)
    prior_uncertainty: float = Field(gt=0.0)
    value: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(gt=0.0)
    evidence_availability: EvidenceAvailability
    evidence_count: int = Field(ge=0)
    conflict: bool = False


class StateVector(StrictModel):
    fatigue: float = Field(ge=0.0, le=1.0)
    stress: float = Field(ge=0.0, le=1.0)
    self_efficacy: float = Field(ge=0.0, le=1.0)

    @classmethod
    def from_mapping(cls, values: dict[str, float]) -> StateVector:
        return cls(
            fatigue=values["fatigue"],
            stress=values["stress"],
            self_efficacy=values["self_efficacy"],
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "fatigue": self.fatigue,
            "stress": self.stress,
            "self_efficacy": self.self_efficacy,
        }


class UncertaintyVector(StrictModel):
    fatigue: float = Field(gt=0.0)
    stress: float = Field(gt=0.0)
    self_efficacy: float = Field(gt=0.0)

    @classmethod
    def from_mapping(cls, values: dict[str, float]) -> UncertaintyVector:
        return cls(
            fatigue=values["fatigue"],
            stress=values["stress"],
            self_efficacy=values["self_efficacy"],
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "fatigue": self.fatigue,
            "stress": self.stress,
            "self_efficacy": self.self_efficacy,
        }


class SignedVector(StrictModel):
    """A vector that may be negative (prediction errors, standardized errors)."""

    fatigue: float
    stress: float
    self_efficacy: float

    @classmethod
    def from_mapping(cls, values: dict[str, float]) -> SignedVector:
        return cls(
            fatigue=values["fatigue"],
            stress=values["stress"],
            self_efficacy=values["self_efficacy"],
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "fatigue": self.fatigue,
            "stress": self.stress,
            "self_efficacy": self.self_efficacy,
        }


class PredictionError(StrictModel):
    raw: SignedVector
    standardized: SignedVector


class NextDayPrior(StrictModel):
    value: StateVector
    uncertainty: UncertaintyVector
    source: str


class SourceTraitModel(StrictModel):
    model: str
    schema_version: str
    calibration_model: str | None = None
    calibration_version: str | None = None
    reference_population: str | None = None
    domains_used: list[str] = Field(default_factory=lambda: ["N", "E", "O", "A", "C"])


class EvidenceMetadata(StrictModel):
    extractor: str
    extractor_version: str
    extraction_status: Literal["no_reflection", "ok", "failed"]
    reflection_fields_present: list[ReflectionField] = Field(default_factory=list)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    conflict_states: list[StateName] = Field(default_factory=list)
    rejected_item_count: int = 0
    error: str | None = None


class DynamicStateProfile(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    model: Literal["DDSR-V1"] = "DDSR-V1"
    model_version: str = "ddsr_v1"
    config_version: str
    date: date
    cold_start: bool
    gap_days: int = Field(ge=0)
    source_trait_model: SourceTraitModel

    fatigue: StateEstimate
    stress: StateEstimate
    self_efficacy: StateEstimate

    prior: StateVector
    current_posterior: StateVector
    prediction_error: PredictionError
    next_day_prior: NextDayPrior

    behavioral_indicators: BehavioralIndicators
    evidence: EvidenceMetadata

    passive_context_used: bool = False
    passive_context: PassiveContext | None = None

    limitations: list[str] = Field(
        default_factory=lambda: [
            "State scale is a 0-1 engineering scale, not a clinical or published scale.",
            (
                "Persistence and noise parameters are engineering initializations, "
                "not estimated coefficients."
            ),
            "V1 stores prediction errors but does not learn personalized transition parameters.",
        ]
    )
