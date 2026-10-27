"""Agent-side context contracts.

These are the *only* shapes the graph knows about. The concrete database reads
live in the application layer (:class:`app.application.context.RepoContextBuilder`)
which implements :class:`ContextBuilderProtocol` - so no node ever touches a
session, a repository or a SQL statement.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.agent.features import FeedbackSignal, PlanProgress, UserFeatureSet
from app.domain.models.enums import CognitiveLoad, Priority, TaskKind, TaskStatus
from app.domain.scheduling.schedule_result import FixedEvent
from app.user_models.contracts import UserModelContext


class MemoryKind(StrEnum):
    """The three memory types the agent consumes (all structured, no vectors)."""

    SEMANTIC = "semantic"  # stable facts / preferences / abilities
    EPISODIC = "episodic"  # concrete things that happened
    PROCEDURAL = "procedural"  # "how this user should be scheduled" rules of thumb


class MemoryItem(BaseModel):
    """One structured memory record.

    ``key`` is a stable slug (``"chronotype"``, ``"late_night_completion"``) and
    ``value`` is JSON-serialisable so it survives checkpointing.
    """

    kind: MemoryKind
    key: str
    value: dict = Field(default_factory=dict)
    summary: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = "derived"


class UserPreferences(BaseModel):
    """Scheduling preferences resolved from the user profile + request."""

    available_minutes_per_day: int = Field(default=480, ge=1)
    daily_limit_minutes: int = Field(default=300, ge=1)
    buffer_minutes: int = Field(default=15, ge=0)
    high_cognitive_max_per_day: int = Field(default=2, ge=1)
    #: HARD cap for one goal's total scheduled minutes on a single day.
    max_daily_minutes_per_goal: int = Field(default=120, ge=1)
    day_start: time = time(8, 0)
    day_end: time = time(22, 0)
    preferred_time_slots: dict[str, str] = Field(default_factory=dict)
    unavailable_weekdays: list[int] = Field(default_factory=list)


class CurrentTaskSnapshot(BaseModel):
    """Read-only view of a task on the current plan version."""

    task_id: int
    title: str
    status: TaskStatus
    #: Persisted goal id - carried through micro-adjustment so the goal chain
    #: survives into a later full replan.
    goal_id: int | None = None
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM
    priority: Priority = Priority.MEDIUM
    estimated_duration: int = 60
    predicted_duration: int | None = None
    scheduled_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    subject: str | None = None
    is_flexible: bool = True
    task_kind: TaskKind = TaskKind.ONE_OFF
    #: Cross-version semantic work-unit identity (for replan dedup).
    work_unit_key: str | None = None
    chunk_index: int | None = None
    series_id: str | None = None
    series_index: int | None = None
    occurrence_date: date | None = None
    target_amount: int | None = None
    target_unit: str | None = None


class CurrentPlanSnapshot(BaseModel):
    """Read-only view of the plan being adjusted."""

    plan_id: int
    version: int
    status: str = "active"
    title: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    tasks: list[CurrentTaskSnapshot] = Field(default_factory=list)

    def pending_tasks(self) -> list[CurrentTaskSnapshot]:
        return [
            task
            for task in self.tasks
            if task.status not in {TaskStatus.COMPLETED, TaskStatus.SKIPPED}
        ]


class PlanningContext(BaseModel):
    """Everything the agent needs, assembled by the Context Builder.

    Flow: Database -> Context Builder (application) -> PlanningContext -> state.
    """

    user_id: int
    execution_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    profile: dict = Field(default_factory=dict)
    preferences: UserPreferences = Field(default_factory=UserPreferences)

    # Memory layers (structured; semantic/episodic/procedural).
    semantic_memory: list[MemoryItem] = Field(default_factory=list)
    episodic_memory: list[MemoryItem] = Field(default_factory=list)
    procedural_memory: list[MemoryItem] = Field(default_factory=list)

    # Execution state.
    user_features: UserFeatureSet | None = None
    progress: PlanProgress | None = None
    current_plan: CurrentPlanSnapshot | None = None
    recent_feedback: list[FeedbackSignal] = Field(default_factory=list)
    #: Imported immovable events expanded over a rolling window (today..+90d).
    fixed_events: list[FixedEvent] = Field(default_factory=list)

    #: Typed Level 1/2/3 snapshot built by the application layer. This is the
    #: only user-model shape the agent consumes; it is never re-derived in a
    #: node and never includes raw SQLAlchemy rows.
    user_model: UserModelContext | None = None
    # Free-form note the user attached to this run (adjustment / feedback text).
    user_note: str | None = None
    assembled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def all_memory(self) -> list[MemoryItem]:
        return [*self.semantic_memory, *self.episodic_memory, *self.procedural_memory]


@runtime_checkable
class ContextBuilderProtocol(Protocol):
    """Application-layer implementation reads the database; the agent does not."""

    def build(
        self,
        user_id: int,
        *,
        plan_id: int | None = None,
        user_note: str | None = None,
        profile_overrides: dict | None = None,
    ) -> PlanningContext: ...
