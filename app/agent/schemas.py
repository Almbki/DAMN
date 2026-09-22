"""Structured schemas for every Agent node.

Rule: agents MUST return these Pydantic objects. Free-form LLM text is never
allowed to flow into the plan pipeline - the graph parses into these schemas.
"""

from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.enums import CognitiveLoad, LoadLevel, Priority, TimeOfDay
from app.domain.rules.base import RuleViolation


class LLMOutput(BaseModel):
    """Base for schemas a model must produce.

    ``extra="forbid"`` is essential: without it any JSON object validates
    against an all-optional schema, so a wrong/empty model answer would silently
    become an empty result instead of falling back deterministically.
    """

    model_config = ConfigDict(extra="forbid")


class AnalyzedGoal(LLMOutput):
    goal_id: int
    title: str
    objective: str = ""
    subtasks: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class GoalAnalysisResult(LLMOutput):
    """Output of the ``goal_analysis`` node."""

    goals: list[AnalyzedGoal] = Field(default_factory=list)
    summary: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class TheoreticalItem(LLMOutput):
    """Theory-derived expected workload for one unit of work."""

    title: str
    learning_content: str = ""
    subtasks: list[str] = Field(default_factory=list)
    video_minutes: int = Field(default=0, ge=0)
    reading_minutes: int = Field(default=0, ge=0)
    practice_minutes: int = Field(default=0, ge=0)
    total_minutes: int = Field(default=0, ge=0)
    difficulty: float = Field(default=3.0, ge=1, le=5)
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM


class TheoreticalAnalysisResult(LLMOutput):
    """Output of the ``theoretical_analysis`` node."""

    items: list[TheoreticalItem] = Field(default_factory=list)
    total_theoretical_minutes: int = Field(default=0, ge=0)
    overall_difficulty: float = Field(default=3.0, ge=1, le=5)
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class UserSituationResult(LLMOutput):
    """Output of the ``user_situation_analysis`` node.

    This is the bridge between the theoretical workload and the *actual* user.
    """

    duration_factor: float = Field(default=1.0, gt=0)
    completion_ability: float = Field(default=0.7, ge=0.0, le=1.0)
    stress_state: float = Field(default=5.0, ge=0.0, le=10.0)
    fatigue_state: LoadLevel = LoadLevel.MODERATE
    recommended_time_slot: TimeOfDay = TimeOfDay.MORNING
    predicted_duration: dict[int, int] = Field(default_factory=dict)
    predicted_completion_probability: dict[int, float] = Field(default_factory=dict)
    should_reduce_load: bool = False
    #: Optional LLM narrative. The numbers above stay authoritative.
    narrative: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class GeneratedTaskDraft(LLMOutput):
    """A task proposed by the ``plan_generation`` node (not yet scheduled)."""

    title: str
    description: str | None = None
    goal_id: int | None = None
    estimated_duration: int = Field(default=60, ge=1)
    predicted_duration: int | None = Field(default=None, ge=1)
    # ML outputs must survive into the plan (previously dropped on the floor).
    completion_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    recommended_time_slot: TimeOfDay | None = None
    predicted_stress: float | None = Field(default=None, ge=0.0, le=10.0)
    #: Truthful origin of the numbers above (mock:statistical | xgboost-v1 | ...).
    #: Recorded into ``prediction_logs`` so predictions can be scored later.
    prediction_source: str | None = None
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM
    priority: Priority = Priority.MEDIUM
    subject: str | None = None
    standards: list[str] = Field(default_factory=list)
    deadline: datetime | None = None
    order_index: int = 0


class PlanGenerationResult(LLMOutput):
    """Output of the ``plan_generation`` node."""

    title: str = ""
    start_date: date | None = None
    end_date: date | None = None
    tasks: list[GeneratedTaskDraft] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class RuleValidationResult(BaseModel):
    """Output of the ``rule_validation`` node."""

    passed: bool = True
    violations: list[RuleViolation] = Field(default_factory=list)


class PlanRepairResult(LLMOutput):
    """Output of the ``plan_repair`` node."""

    repaired: bool = False
    changed_task_ids: list[int] = Field(default_factory=list)
    tasks: list[GeneratedTaskDraft] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request classification
# ---------------------------------------------------------------------------
class RequestIntent(StrEnum):
    """What the caller is asking the agent to do."""

    INITIAL_PLAN = "INITIAL_PLAN"
    ADJUST_PREVIEW = "ADJUST_PREVIEW"
    USER_ADJUSTMENT = "USER_ADJUSTMENT"
    REPLAN_REQUEST = "REPLAN_REQUEST"
    FEEDBACK_DRIVEN = "FEEDBACK_DRIVEN"


class ClassifyResult(BaseModel):
    """Output of the ``classify_request`` node (deterministic first version)."""

    intent: RequestIntent = RequestIntent.INITIAL_PLAN
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
class PreviewTask(BaseModel):
    """One task as shown to the user in the preview."""

    order_index: int
    title: str
    description: str | None = None
    goal_id: int | None = None
    subject: str | None = None
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM
    priority: Priority = Priority.MEDIUM
    estimated_duration: int = 60
    predicted_duration: int | None = None
    completion_probability: float | None = None
    recommended_time_slot: TimeOfDay | None = None
    standards: list[str] = Field(default_factory=list)
    scheduled_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None


class PreviewPayload(BaseModel):
    """The paused preview returned to the user for confirm/adjust."""

    thread_id: str
    title: str = ""
    start_date: date | None = None
    end_date: date | None = None
    tasks: list[PreviewTask] = Field(default_factory=list)
    rule_violations: list[RuleViolation] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    adjustment_count: int = 0
    max_adjustments: int = 2
    can_adjust: bool = True
    notes: list[str] = Field(default_factory=list)


class PreviewDecision(BaseModel):
    """What the user did with the preview (resume payload of the interrupt)."""

    action: Literal["confirm", "adjust"] = "confirm"
    feedback: str | None = None


class PreviewAdjustmentRejected(BaseModel):
    """Returned when the adjustment budget is exhausted."""

    rejected: bool = True
    adjustment_count: int = 0
    max_adjustments: int = 2
    reason: str = ""
    message: str = ""


# ---------------------------------------------------------------------------
# Errors / final output
# ---------------------------------------------------------------------------
class AgentError(BaseModel):
    """A recoverable error recorded during a run (never fatal by itself)."""

    node: str
    kind: str
    message: str
    recovered: bool = True


class FinalPlanPayload(BaseModel):
    """The finalised plan produced by ``plan_finalization``."""

    title: str = ""
    start_date: date | None = None
    end_date: date | None = None
    tasks: list[GeneratedTaskDraft] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    trigger_source: str = "initial_plan"
    rule_violations: list[RuleViolation] = Field(default_factory=list)
