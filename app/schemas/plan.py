"""Plan API schemas."""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.enums import (
    CognitiveLoad,
    GoalStatus,
    GoalType,
    PlanStatus,
    Priority,
    ReplanTriggerType,
    TimeOfDay,
)
from app.schemas.common import ViolationRead
from app.schemas.task import TaskRead
from app.schemas.user import DataSufficiency


class PlanGoalCreate(BaseModel):
    """A goal supplied inside a plan-generation request.

    Distinct from :class:`app.schemas.goal.GoalCreate` (the `/goals` CRUD
    surface): no `status`, and `subject`/`task_type` are optional hints.
    """

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    goal_type: GoalType = GoalType.SHORT_TERM
    deadline: datetime | None = None
    priority: Priority = Priority.MEDIUM
    estimated_minutes: int | None = Field(default=None, ge=1)
    subject: str | None = None
    task_type: str | None = None


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    goal_type: GoalType
    deadline: datetime | None = None
    priority: Priority
    status: GoalStatus
    estimated_minutes: int | None = None


class PlanGenerateRequest(BaseModel):
    """Request body of ``POST /plans/generate``.

    The four scheduling caps are **optional**: send them to override this plan
    only, omit them to use the user's stored preferences. (They used to carry
    defaults, which made an omitted value indistinguishable from an explicit
    one — and they were silently dropped downstream.)
    """

    goals: list[PlanGoalCreate] = Field(min_length=1)
    start_date: date | None = None
    end_date: date | None = None
    plan_title: str | None = None
    available_minutes_per_day: int | None = Field(default=None, ge=1, le=1440)
    daily_limit_minutes: int | None = Field(default=None, ge=1, le=1440)
    buffer_minutes: int | None = Field(default=None, ge=0, le=120)
    high_cognitive_max_per_day: int | None = Field(default=None, ge=1, le=10)
    user_profile: dict = Field(default_factory=dict)
    execution_weight: float | None = Field(default=None, ge=0.0, le=1.0)


class PreviewTaskRead(BaseModel):
    """One task as shown in a plan preview."""

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


class PreviewRead(BaseModel):
    """The paused preview returned to the client."""

    thread_id: str
    title: str = ""
    start_date: date | None = None
    end_date: date | None = None
    tasks: list[PreviewTaskRead] = Field(default_factory=list)
    confidence: float = 0.5
    adjustment_count: int = 0
    max_adjustments: int = 2
    can_adjust: bool = True
    violations: list[ViolationRead] = Field(default_factory=list)


class PreviewResponse(BaseModel):
    thread_id: str
    preview: PreviewRead
    plan_id: int | None = None
    goals_persisted: int = 0
    #: True when the run continued with a fallback (no history, LLM unavailable,
    #: context build failure). `warnings` says why - never silent.
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)


class ConfirmRequest(BaseModel):
    thread_id: str = Field(min_length=1)


class ConfirmResponse(BaseModel):
    plan: PlanRead
    adjustment_count: int = 0
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)


class AdjustRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    feedback: str = Field(min_length=1, max_length=2000)


class AdjustResponse(BaseModel):
    """Result of a bounded preview adjustment.

    When ``budget_exhausted`` is true the user must start executing: the graph
    refused to call the LLM again and finalised the plan instead.
    """

    thread_id: str
    preview: PreviewRead | None = None
    budget_exhausted: bool = False
    final_plan: PlanRead | None = None
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)


class FeedbackAdjustmentRead(BaseModel):
    """Agent decision attached to a feedback submission."""

    route: str
    severity: str = "NONE"
    reasons: list[str] = Field(default_factory=list)
    source: str = "fallback"
    new_plan_id: int | None = None
    degraded: bool = False


# ---------------------------------------------------------------------------
# Draft decomposition (frontend contract: decompose -> confirm)
# ---------------------------------------------------------------------------
class DecomposeGoal(BaseModel):
    """One item from the frontend's "待拆解清单"."""

    title: str = Field(min_length=1)
    priority: int = Field(default=2, ge=1, le=3)
    deadline: date | None = None
    notes: str | None = None


class DecomposeRequest(BaseModel):
    """``POST /plans/decompose`` - multi-goal decomposition into a draft.

    Send ``draft_id`` + ``feedback`` to regenerate an existing draft (bounded by
    ``AGENT_MAX_PREVIEW_ADJUSTMENTS``).
    """

    goals: list[DecomposeGoal] = Field(min_length=1)
    draft_id: str | None = None
    feedback: str | None = None


class DecomposeDraftTask(BaseModel):
    title: str
    #: 1 = low, 2 = medium, >=3 = high (clamped to the contract's 1..3 range).
    priority: int = Field(ge=1, le=3)
    estimated_minutes: int = Field(ge=1)
    start_time: time | None = None
    end_time: time | None = None
    #: 0-based index into the request's ``goals[]`` this task came from.
    source_index: int = 0


class DecomposeDay(BaseModel):
    date: date
    tasks: list[DecomposeDraftTask] = Field(default_factory=list)


class DecomposeResponse(BaseModel):
    draft_id: str
    days: list[DecomposeDay] = Field(default_factory=list)


class ConfirmDraftRequest(BaseModel):
    draft_id: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Plan change history
# ---------------------------------------------------------------------------
class PlanChangeDayRead(BaseModel):
    date: date
    added: int = 0
    moved: int = 0
    removed: int = 0
    summary: str = ""
    task_ids: list[int] = Field(default_factory=list)


class PlanChangeRead(BaseModel):
    id: int
    trigger_type: ReplanTriggerType
    reason: str = ""
    old_version: int
    new_version: int
    created_at: datetime
    days: list[PlanChangeDayRead] = Field(default_factory=list)


class PlanRead(BaseModel):
    id: int
    user_id: int
    version: int
    status: PlanStatus
    title: str | None = None
    start_date: date
    end_date: date
    parent_plan_id: int | None = None
    confidence: float
    created_at: datetime
    tasks: list[TaskRead] = Field(default_factory=list)
    goals: list[GoalRead] = Field(default_factory=list)


class PlanListItem(BaseModel):
    id: int
    version: int
    status: PlanStatus
    title: str | None = None
    start_date: date
    end_date: date
    confidence: float
    created_at: datetime
    task_count: int = 0
    completed_count: int = 0


class PlanGenerateResponse(BaseModel):
    """``POST /plans/generate`` returns a job id immediately; poll/stream next."""

    job_id: str
    status: str
    plan_id: int | None = None
    events_url: str
    plan: PlanRead | None = None


class ReplanEligibilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    eligible: bool
    reason: str = ""
    next_eligible_at: datetime | None = None
    last_replan_at: datetime | None = None
    cooldown_hours: int = 0


class ReplanRequest(BaseModel):
    trigger_type: ReplanTriggerType = ReplanTriggerType.MANUAL
    reason: str | None = None
    from_date: date | None = None


class ReplanResponse(BaseModel):
    plan_id: int
    old_version: int
    new_version: int
    changed_task_ids: list[int] = Field(default_factory=list)
    reason: str = ""
    trigger_type: ReplanTriggerType


class DailyCompletionRead(BaseModel):
    date: str
    total_tasks: int = 0
    completed_tasks: int = 0
    completion_rate: float = 0.0
    planned_minutes: int = 0


class InsightRead(BaseModel):
    plan_id: int
    total_tasks: int = 0
    completed_tasks: int = 0
    completion_rate: float = 0.0
    total_planned_minutes: int = 0
    total_actual_minutes: int = 0
    avg_stress: float | None = None
    avg_energy: float | None = None
    high_cognitive_minutes: int = 0
    predicted_vs_actual_ratio: float | None = None
    cognitive_load_breakdown: dict[str, int] = Field(default_factory=dict)
    daily: list[DailyCompletionRead] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    #: Whether there is enough recorded history to trust the numbers above.
    data_sufficiency: DataSufficiency | None = None
    #: Human-readable reasons behind the summary (Chinese UI copy).
    drivers: list[str] | None = None
