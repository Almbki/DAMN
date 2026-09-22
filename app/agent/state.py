"""LangGraph state and graph input contract.

The state is a ``TypedDict`` so LangGraph can merge node updates. All complex
values are Pydantic models from :mod:`app.agent.schemas` or the domain layer.

Reminder: LangGraph only orchestrates. It never opens a DB session and never
decides hard constraints - the Rule Engine does.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TypedDict

from pydantic import BaseModel, Field

from app.agent.schemas import (
    GeneratedTaskDraft,
    GoalAnalysisResult,
    PlanGenerationResult,
    PlanRepairResult,
    RuleValidationResult,
    TheoreticalAnalysisResult,
    UserSituationResult,
)
from app.domain.models.enums import GoalType, Priority
from app.domain.rules.base import RuleViolation
from app.domain.scheduling.schedule_result import CandidateSchedule
from app.ml.base import UserFeatureSet


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


class GenerationRequest(BaseModel):
    """Input contract of the LangGraph planning pipeline."""

    user_id: int
    goals: list[GoalInput] = Field(default_factory=list)
    start_date: date
    end_date: date
    plan_title: str | None = None
    # User scheduling preferences.
    available_minutes_per_day: int = Field(default=480, ge=1)
    daily_limit_minutes: int = Field(default=300, ge=1)
    buffer_minutes: int = Field(default=15, ge=0)
    high_cognitive_max_per_day: int = Field(default=2, ge=1)
    # Free-form profile carried into prompts / features.
    user_profile: dict = Field(default_factory=dict)
    execution_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class PlannerState(TypedDict, total=False):
    """Shared state flowing through the LangGraph state machine."""

    # --- required inputs ---
    user_id: int
    goals: list[GoalInput]
    user_profile: dict
    request: GenerationRequest

    # --- node outputs ---
    goal_analysis: GoalAnalysisResult
    theoretical_workload: TheoreticalAnalysisResult
    user_situation: UserSituationResult
    plan_draft: PlanGenerationResult
    candidate_plan: CandidateSchedule
    rule_validation: RuleValidationResult
    rule_violations: list[RuleViolation]
    repaired_plan: PlanRepairResult

    # --- flattened ML outputs (spec-mandated state keys) ---
    predicted_duration: dict[int, int]
    predicted_completion_probability: dict[int, float]
    stress_estimation: float

    # --- control / output ---
    repair_attempts: int
    max_repair_attempts: int
    final_tasks: list[GeneratedTaskDraft]
    final_plan: CandidateSchedule | None
    confidence: float
    notes: list[str]
    events: list[dict]

    # --- optional dependency injection (set by the Service) ---
    # user_features is built by the Service from TaskExecution + Feedback +
    # UserModel (the graph itself never touches the database).
    user_features: UserFeatureSet
    # goal_key (1-based goal index) -> persisted goal primary key.
    goal_id_map: dict[int, int]
    # 环节 2 画像提示词: portrait JSON built by the Service, injected into the
    # plan-generation prompt. ``None`` when the user has no profile.
    profile_prompt: dict | None
    # Optional LLM client (infrastructure) injected by the Service.
    llm: object
    theoretical_agent: object
    situation_agent: object
    predictors: object
    rule_engine: object
    scheduler: object
