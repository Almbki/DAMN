"""Agent state and run-scoped context.

Two clearly separated concepts:

``PlannerContext`` (dataclass)
    Run-scoped *dependencies*: scheduler, rule engine, predictors, LLM, context
    builder, config, event sink. Injected by the application layer, never stored
    in the graph state. Because it holds live objects it is **not** checkpointed.

``PlannerState`` (TypedDict)
    The agent's working state. Only JSON-serialisable data lives here so
    LangGraph can checkpoint it. Accumulating fields use ``operator.add``
    reducers; ``rule_violations`` deliberately has no reducer (it must always
    hold the *latest* validation result).

Nothing here talks to the database - the Context Builder does that in the
application layer.
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field

from app.agent.context import ContextBuilderProtocol, CurrentPlanSnapshot, PlanningContext
from app.agent.schemas import (
    AgentError,
    ClassifyResult,
    FinalPlanPayload,
    GoalAnalysisResult,
    PlanGenerationResult,
    PlanRepairResult,
    PreviewPayload,
    RequestIntent,
    RuleValidationResult,
    TheoreticalAnalysisResult,
    UserSituationResult,
)
from app.domain.models.enums import GoalType, Priority
from app.domain.rules.base import RuleEngine, RuleViolation
from app.domain.scheduling.schedule_result import CandidateSchedule
from app.domain.scheduling.scheduler import Scheduler
from app.ml.base import AdjustmentPrediction, AdjustmentRoute, PlanProgress
from app.ml.predictors import PredictorSet

# ---------------------------------------------------------------------------
# Agent configuration (from Settings, resolved by the application layer)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class AgentConfig:
    """Tunables the graph reads. Kept out of state so it needs no checkpointing."""

    max_preview_adjustments: int = 2
    max_repair_attempts: int = 2
    llm_max_retries: int = 2
    llm_timeout_seconds: float = 30.0
    graph_version: str = "planner-v1"
    prompt_version: str = "v1"
    trace_enabled: bool = True
    #: Adjustment policy (see app.agent.router.AdjustmentRouter).
    low_completion_threshold: float = 0.3
    max_consecutive_micro_adjustments: int = 2


@dataclass(slots=True)
class PlannerContext:
    """Live collaborators injected into every node via LangGraph's runtime context."""

    scheduler: Scheduler
    rule_engine: RuleEngine
    predictors: PredictorSet
    config: AgentConfig = field(default_factory=AgentConfig)
    llm: Any | None = None  # StructuredLLM (app.agent.llm); None -> deterministic fallback
    context_builder: ContextBuilderProtocol | None = None
    # Lazily built tool registry (see PlannerContext.tool()).
    tools: Any | None = None
    # Event sink: (event_name, payload). The Service turns these into SSE frames.
    emit: Callable[[str, dict], None] | None = None

    def tool(self, name: str) -> Any:
        """Return a tool by name, building the default registry on first use."""
        if self.tools is None:
            from app.agent.tools import default_registry

            self.tools = default_registry(
                llm=self.llm,
                predictors=self.predictors,
                scheduler=self.scheduler,
                rule_engine=self.rule_engine,
            )
        return self.tools.get(name)

    def publish(self, event: str, payload: dict | None = None) -> None:
        """Emit an agent event if a sink is attached (never raises)."""
        if self.emit is None:
            return
        try:
            self.emit(event, payload or {})
        except Exception:  # pragma: no cover - event emission must never break a run
            pass


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class GoalInput(BaseModel):
    """One goal supplied by the client when requesting plan generation."""

    title: str
    description: str | None = None
    goal_type: GoalType = GoalType.SHORT_TERM
    deadline: datetime | None = None
    priority: Priority = Priority.MEDIUM
    estimated_minutes: int | None = Field(default=None, ge=1)
    subject: str | None = None
    task_type: str | None = None


class PreferenceInput(BaseModel):
    """Client-supplied scheduling preferences (optional overrides)."""

    available_minutes_per_day: int = Field(default=480, ge=1)
    daily_limit_minutes: int = Field(default=300, ge=1)
    buffer_minutes: int = Field(default=15, ge=0)
    high_cognitive_max_per_day: int = Field(default=2, ge=1)
    day_start: str = "08:00"
    day_end: str = "22:00"
    preferred_time_slots: dict[str, str] = Field(default_factory=dict)
    unavailable_weekdays: list[int] = Field(default_factory=list)


class PlannerRequest(BaseModel):
    """Unified input contract of the agent graphs.

    One request shape covers initial planning, preview adjustment and feedback
    cycles so the Service never has to know graph internals.
    """

    user_id: int
    trigger_type: RequestIntent = RequestIntent.INITIAL_PLAN
    goals: list[GoalInput] = Field(default_factory=list)
    # Set for everything that operates on an existing plan version.
    plan_id: int | None = None
    user_note: str | None = None
    plan_title: str | None = None
    start_date: date
    end_date: date
    preferences: PreferenceInput | None = None
    # Basic profile fields (MBTI is a soft profile input, never a diagnosis).
    mbti: str | None = None
    execution_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    profile: dict = Field(default_factory=dict)


#: Backwards-compatible alias (the Service/API used ``GenerationRequest``).
GenerationRequest = PlannerRequest


class PreviewActionRequest(BaseModel):
    """Resume payload for the paused preview."""

    user_id: int
    thread_id: str
    action: str = "confirm"  # "confirm" | "adjust"
    feedback: str | None = None


class FeedbackCycleRequest(BaseModel):
    """Input of the feedback loop graph."""

    user_id: int
    plan_id: int
    user_note: str | None = None


class ReplanTriggerRequest(BaseModel):
    """Explicit user-initiated replan."""

    user_id: int
    plan_id: int
    reason: str | None = None
    trigger_source: str = "user_request"


# ---------------------------------------------------------------------------
# Run metadata / tool records
# ---------------------------------------------------------------------------


class RunMetadata(BaseModel):
    """Non-sensitive run bookkeeping (no prompts, no private text)."""

    run_id: str = ""
    user_id: int = 0
    trigger_type: str = "initial_plan"
    graph_version: str = "planner-v1"
    prompt_version: str = "v1"
    started_at: datetime | None = None
    nodes_executed: list[str] = Field(default_factory=list)
    llm_calls: int = 0


class ToolCallRecord(BaseModel):
    """One tool invocation (name, ok/failed, latency, short summary)."""

    tool: str
    ok: bool = True
    duration_ms: int = 0
    summary: str = ""
    used_llm: bool = False
    error: str | None = None


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class PlannerState(TypedDict, total=False):
    """Working state of the agent graphs (serialisable only)."""

    # --- inputs ---
    request: PlannerRequest
    user_id: int
    goals: list[GoalInput]
    user_context: PlanningContext | None
    current_plan: CurrentPlanSnapshot | None
    goal_id_map: dict[int, int]

    # --- analysis ---
    classify: ClassifyResult
    goal_analysis: GoalAnalysisResult
    theoretical_analysis: TheoreticalAnalysisResult
    user_situation: UserSituationResult

    # --- ML ---
    ml_prediction: AdjustmentPrediction | None
    predicted_duration: dict[int, int]
    predicted_completion_probability: dict[int, float]
    stress_estimation: float
    #: Truthful origin of the per-task predictions (goes into prediction_logs).
    prediction_source: str

    # --- planning ---
    plan_draft: PlanGenerationResult
    candidate_plan: CandidateSchedule
    rule_validation: RuleValidationResult
    rule_violations: list[RuleViolation]  # NO reducer: always the latest result
    repaired_plan: PlanRepairResult

    # --- preview / adjustment ---
    preview: PreviewPayload | None
    user_adjustment: str | None
    adjustment_count: int
    adjustment_rejected: bool

    # --- routing / outcome ---
    route: AdjustmentRoute | None
    #: Multiplier applied to the daily limits (set by MICRO_ADJUST, 1.0 otherwise).
    limit_factor: float
    replan_reason: str | None
    final_plan: FinalPlanPayload | None
    progress: PlanProgress | None

    # --- control ---
    repair_attempts: int
    max_repair_attempts: int
    confidence: float

    # --- accumulators (reducers) ---
    notes: Annotated[list[str], operator.add]
    errors: Annotated[list[AgentError], operator.add]
    tool_results: Annotated[list[ToolCallRecord], operator.add]

    # --- metadata ---
    metadata: RunMetadata


__all__ = [
    "AgentConfig",
    "FeedbackCycleRequest",
    "GenerationRequest",
    "GoalInput",
    "PlannerContext",
    "PlannerRequest",
    "PlannerState",
    "PreferenceInput",
    "PreviewActionRequest",
    "ReplanTriggerRequest",
    "RunMetadata",
    "ToolCallRecord",
]
