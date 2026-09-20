"""Plan API schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.enums import (
    GoalStatus,
    GoalType,
    PlanStatus,
    Priority,
    ReplanTriggerType,
)
from app.schemas.task import TaskRead


class GoalCreate(BaseModel):
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
    """Request body of ``POST /plans/generate``."""

    goals: list[GoalCreate] = Field(min_length=1)
    start_date: date | None = None
    end_date: date | None = None
    plan_title: str | None = None
    available_minutes_per_day: int = Field(default=480, ge=1, le=1440)
    daily_limit_minutes: int = Field(default=300, ge=1, le=1440)
    buffer_minutes: int = Field(default=15, ge=0, le=120)
    high_cognitive_max_per_day: int = Field(default=2, ge=1, le=10)
    user_profile: dict = Field(default_factory=dict)
    execution_weight: float | None = Field(default=None, ge=0.0, le=1.0)


class GenerationEventRead(BaseModel):
    node: str
    stage: str
    status: str
    summary: str = ""
    payload: dict = Field(default_factory=dict)
    progress: float = 0.0
    timestamp: datetime


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
