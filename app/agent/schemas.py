"""Structured schemas for every Agent node.

Rule: agents MUST return these Pydantic objects. Free-form LLM text is never
allowed to flow into the plan pipeline - the graph parses into these schemas.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domain.models.enums import CognitiveLoad, LoadLevel, Priority, TimeOfDay
from app.domain.rules.base import RuleViolation


class AnalyzedGoal(BaseModel):
    goal_id: int
    title: str
    objective: str = ""
    subtasks: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class GoalAnalysisResult(BaseModel):
    """Output of the ``goal_analysis`` node."""

    goals: list[AnalyzedGoal] = Field(default_factory=list)
    summary: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class TheoreticalItem(BaseModel):
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


class TheoreticalAnalysisResult(BaseModel):
    """Output of the ``theoretical_analysis`` node."""

    items: list[TheoreticalItem] = Field(default_factory=list)
    total_theoretical_minutes: int = Field(default=0, ge=0)
    overall_difficulty: float = Field(default=3.0, ge=1, le=5)
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class UserSituationResult(BaseModel):
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
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class GeneratedTaskDraft(BaseModel):
    """A task proposed by the ``plan_generation`` node (not yet scheduled)."""

    title: str
    description: str | None = None
    goal_id: int | None = None
    estimated_duration: int = Field(default=60, ge=1)
    predicted_duration: int | None = Field(default=None, ge=1)
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM
    priority: Priority = Priority.MEDIUM
    subject: str | None = None
    standards: list[str] = Field(default_factory=list)
    deadline: datetime | None = None
    order_index: int = 0


class PlanGenerationResult(BaseModel):
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


class PlanRepairResult(BaseModel):
    """Output of the ``plan_repair`` node."""

    repaired: bool = False
    changed_task_ids: list[int] = Field(default_factory=list)
    tasks: list[GeneratedTaskDraft] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
