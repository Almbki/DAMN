"""``RepoContextBuilder`` - Database -> Memory -> PlanningContext.

Layer note: this lives in the *application* layer because it needs repositories.
`app/agent/context.py` defines the protocol it satisfies, and the memory
*derivation* helpers are pure functions in `app/agent/memory/`. That keeps the
"agents never touch the DB" rule intact while still giving the graph rich
context.
"""

from __future__ import annotations

from datetime import date, time

from sqlalchemy.orm import Session

from app.agent.context import (
    CurrentPlanSnapshot,
    CurrentTaskSnapshot,
    MemoryItem,
    MemoryKind,
    PlanningContext,
    UserPreferences,
)
from app.agent.memory import (
    build_episodic_memory,
    build_semantic_memory,
    derive_procedural_memory,
)
from app.application.preferences import effective_scheduling_preferences
from app.domain.models import AgentMemory, Goal, Task
from app.domain.models.enums import TaskStatus
from app.infrastructure.database.repositories import (
    AgentMemoryRepository,
    FeedbackRepository,
    GoalRepository,
    PlanRepository,
    TaskExecutionRepository,
    TaskRepository,
    UserRepository,
)
from app.ml.base import FeedbackSignal, PlanProgress

DEFAULT_DAY_START = time(8, 0)
DEFAULT_DAY_END = time(22, 0)
#: How many recent check-ins the planner sees.
FEEDBACK_WINDOW = 14


def merge_memory(derived: list[MemoryItem], stored: list[AgentMemory]) -> list[MemoryItem]:
    """Overlay persisted memory on freshly derived memory.

    Persisted rows win on ``(kind, key)`` - they may carry information that
    cannot be re-derived (explicit preferences, consolidated rules of thumb).
    Derived-only keys are kept so a cold user still gets context.
    """
    merged: dict[tuple[MemoryKind, str], MemoryItem] = {
        (item.kind, item.key): item for item in derived
    }
    for row in stored:
        try:
            kind = MemoryKind(row.kind)
        except ValueError:  # unknown kind -> ignore rather than crash planning
            continue
        merged[(kind, row.key)] = MemoryItem(
            kind=kind,
            key=row.key,
            value=row.value,
            summary=row.summary or f"{row.key}: {row.value}",
            confidence=row.confidence,
            source=row.source,
        )
    return list(merged.values())


def _parse_time(value: object, default: time) -> time:
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        try:
            hour, minute = value.strip().split(":", 1)
            return time(int(hour), int(minute))
        except (ValueError, TypeError):
            return default
    return default


class RepoContextBuilder:
    """Builds a :class:`PlanningContext` for one user (optionally one plan)."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._feedback = FeedbackRepository(session)
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)
        self._goals = GoalRepository(session)
        self._memories = AgentMemoryRepository(session)
        # Imported lazily to keep this module free of a service-level cycle.
        from app.application.services.profile_service import ProfileService

        self._profiles = ProfileService(session)

    # -- public API --------------------------------------------------------
    def build(
        self,
        user_id: int,
        *,
        plan_id: int | None = None,
        user_note: str | None = None,
        profile_overrides: dict | None = None,
    ) -> PlanningContext:
        user = self._users.get_by_id(user_id)
        executions = self._executions.list_by_user(user_id)
        feedbacks = self._feedback.list_by_user(user_id)

        profile = dict(user.profile) if user else {}
        if profile_overrides:
            profile.update(profile_overrides)

        plan = (
            self._plans.get_by_id(plan_id)
            if plan_id is not None
            else self._plans.get_latest_by_user(user_id)
        )
        if plan is not None and plan.user_id != user_id:
            plan = None

        tasks = self._tasks.list_by_plan(plan.id) if plan and plan.id is not None else []
        goals = self._goals.list_by_user(user_id)
        goal_by_id = {goal.id: goal for goal in goals}

        # ML features and memory are both driven by the portrait state now, so
        # there is one behavioural model instead of a parallel statistical one.
        features = self._profiles.build_user_features(user_id)
        state = self._profiles.get_state(user_id)
        profile_snapshot = self._profiles.snapshot(user_id)
        profile_decision = self._profiles.replan_decision_for(
            user_id, duration_bias=self._profiles.duration_bias(user_id)
        )

        stored = self._memories.list_by_user(user_id)
        by_kind: dict[str, list[AgentMemory]] = {}
        for row in stored:
            by_kind.setdefault(row.kind, []).append(row)

        # Single source of truth for MBTI: the dedicated users column, falling
        # back to the legacy free-form profile key.
        mbti = (user.mbti_type if user else None) or profile.get("mbti")

        return PlanningContext(
            user_id=user_id,
            mbti=mbti,
            execution_weight=user.execution_weight if user else 0.5,
            profile=profile,
            preferences=self._preferences(
                profile, user.scheduling_preferences if user else None
            ),
            semantic_memory=merge_memory(
                build_semantic_memory(user, state, mbti=mbti),
                by_kind.get(MemoryKind.SEMANTIC.value, []),
            ),
            episodic_memory=merge_memory(
                build_episodic_memory(executions, feedbacks),
                by_kind.get(MemoryKind.EPISODIC.value, []),
            ),
            procedural_memory=merge_memory(
                derive_procedural_memory(state, executions, feedbacks),
                by_kind.get(MemoryKind.PROCEDURAL.value, []),
            ),
            user_features=features,
            progress=self._progress(plan.id, tasks) if plan and plan.id is not None else None,
            current_plan=(
                self._snapshot(plan, tasks, goal_by_id) if plan is not None else None
            ),
            recent_feedback=self._recent_feedback(feedbacks),
            user_note=user_note,
            profile_prompt=profile_snapshot,
            profile_replan=profile_decision.decision,
            profile_replan_reason=profile_decision.reason_code,
        )

    # -- internals ---------------------------------------------------------
    @staticmethod
    def _preferences(profile: dict, stored: dict | None = None) -> UserPreferences:
        """Scheduling prefs: dedicated column > legacy profile keys > defaults."""
        effective = effective_scheduling_preferences(profile, stored)
        return UserPreferences(
            available_minutes_per_day=effective["available_minutes_per_day"],
            daily_limit_minutes=effective["daily_limit_minutes"],
            buffer_minutes=effective["buffer_minutes"],
            high_cognitive_max_per_day=effective["high_cognitive_max_per_day"],
            day_start=_parse_time(profile.get("day_start"), DEFAULT_DAY_START),
            day_end=_parse_time(profile.get("day_end"), DEFAULT_DAY_END),
            preferred_time_slots=dict(profile.get("preferred_time_slots") or {}),
            unavailable_weekdays=list(profile.get("unavailable_weekdays") or []),
        )

    @staticmethod
    def _recent_feedback(feedbacks) -> list[FeedbackSignal]:
        ordered = sorted(feedbacks, key=lambda item: item.date)[-FEEDBACK_WINDOW:]
        return [
            FeedbackSignal(
                date=item.date,
                completion_rate=item.completion_rate,
                stress_level=item.stress_level,
                energy_level=item.energy_level,
                delay_reason=item.delay_reason,
            )
            for item in ordered
        ]

    @staticmethod
    def _snapshot(plan, tasks: list[Task], goal_by_id: dict[int, Goal]) -> CurrentPlanSnapshot:
        snapshots: list[CurrentTaskSnapshot] = []
        for task in tasks:
            goal = goal_by_id.get(task.goal_id) if task.goal_id else None
            subject = None
            if goal is not None:
                subject = (goal.options or {}).get("subject")
            snapshots.append(
                CurrentTaskSnapshot(
                    task_id=task.id or 0,
                    title=task.title,
                    status=task.status,
                    goal_id=task.goal_id,
                    cognitive_load=task.cognitive_load,
                    priority=task.priority,
                    estimated_duration=task.estimated_duration,
                    predicted_duration=task.predicted_duration,
                    scheduled_date=task.scheduled_date,
                    subject=subject,
                )
            )
        return CurrentPlanSnapshot(
            plan_id=plan.id or 0,
            version=plan.version,
            status=getattr(plan.status, "value", str(plan.status)),
            title=plan.title,
            start_date=plan.start_date,
            end_date=plan.end_date,
            tasks=snapshots,
        )

    @staticmethod
    def _progress(plan_id: int, tasks: list[Task]) -> PlanProgress:
        total = len(tasks)
        completed = sum(1 for task in tasks if task.status == TaskStatus.COMPLETED)
        skipped = sum(1 for task in tasks if task.status == TaskStatus.SKIPPED)
        days = {task.scheduled_date for task in tasks if task.scheduled_date}
        today = date.today()
        elapsed = sum(1 for day in days if day < today)
        remaining = sum(1 for day in days if day >= today)
        return PlanProgress(
            plan_id=plan_id,
            version=1,
            total_tasks=total,
            completed_tasks=completed,
            skipped_tasks=skipped,
            completion_rate=round(completed / total, 4) if total else 0.0,
            days_elapsed=elapsed,
            days_remaining=remaining,
        )


__all__ = ["FEEDBACK_WINDOW", "RepoContextBuilder", "merge_memory"]
