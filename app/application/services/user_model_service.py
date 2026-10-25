"""Application seam for the three-layer user model.

Responsibilities
----------------
* Read the persisted Level 1 trait profile and Level 2 state profile.
* Replay DDSR-V1 over real ``task_executions`` + ``feedbacks`` and persist the
  resulting dynamic state (one row per user).
* Build the typed :class:`UserModelContext` consumed by the agent.
* Run Level 3 **shadow** inference after a plan is persisted and append an
  auditable ``shadow_predictions`` row.

It never writes the plan, the schedule or a rule violation: shadow output is not
a control signal.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.models import (
    DailyState,
    PredictionOutcome,
    PredictionSnapshot,
    Task,
    TaskExecution,
)
from app.domain.profile.models import UserStateData
from app.infrastructure.database.repositories import (
    DailyStateRepository,
    FeedbackRepository,
    GoalRepository,
    PredictionOutcomeRepository,
    PredictionSnapshotRepository,
    ShadowPredictionRepository,
    SyntheticDataRepository,
    TaskExecutionRepository,
    TaskRepository,
    UserRepository,
    UserStateRepository,
)
from app.user_models.contracts import (
    DynamicStateSnapshot,
    HistoryBundle,
    Level3Mode,
    TaskPredictionContext,
    UserModelContext,
)
from app.user_models.level2.ddsr.schemas import (
    DayInput,
    PassiveContext,
    ReflectionInput,
)
from app.user_models.level2.ddsr.schemas import TaskExecution as Level2TaskExecution
from app.user_models.level2.ddsr.schemas import TaskPlan as Level2TaskPlan
from app.user_models.runtime import UserModelRuntime
from app.user_models.shadow import Level3ShadowRunner, ShadowPredictionRecord

logger = logging.getLogger(__name__)

DEFAULT_DAY_START = time(8, 0)


def _is_observed_execution(execution) -> bool:
    """True once an execution has an observed outcome, not just a start time."""
    return bool(
        execution.completed
        or execution.finished_at is not None
        or (execution.completion_rate or 0.0) > 0.0
        or execution.actual_duration is not None
    )


_LOCAL_TZ = datetime.now().astimezone().tzinfo


def _as_deadline_naive(value: date | datetime | None) -> datetime | None:
    """Level 2 contract: naive local wall-clock (paired with planned_start)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(_LOCAL_TZ)
        return value.replace(tzinfo=None)
    return datetime.combine(value, time(23, 59))


def _as_deadline_utc(value: date | datetime | None) -> datetime | None:
    """Level 3 contract: aware UTC (compared with prediction_timestamp)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            # Legacy/SQLite rows carry a naive wall clock; keep it truthful by
            # treating it as UTC wall time rather than silently shifting it.
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    return datetime.combine(value, time(23, 59), tzinfo=_LOCAL_TZ).astimezone(UTC)


def _to_utc_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _level3_config_version(runtime: Any) -> str:
    """Recallable Level 3 configuration identity ("" when unavailable)."""
    try:
        return str(runtime.level3.config.config_version)
    except Exception:  # noqa: BLE001 - audit metadata must never break the write
        return ""


def _evidence_summary(snapshot: DynamicStateSnapshot) -> tuple[str, int, bool]:
    """Aggregate the three state estimates into the per-day audit columns."""
    estimates = (snapshot.fatigue, snapshot.stress, snapshot.self_efficacy)
    kinds = {estimate.evidence_availability for estimate in estimates}
    if "reflection_and_task_log" in kinds or {"reflection_only", "task_log_only"} <= kinds:
        availability = "reflection_and_task_log"
    elif "reflection_only" in kinds:
        availability = "reflection_only"
    elif "task_log_only" in kinds:
        availability = "task_log_only"
    else:
        availability = "none"
    return (
        availability,
        sum(estimate.evidence_count for estimate in estimates),
        any(estimate.conflict for estimate in estimates),
    )


class UserModelService:
    def __init__(self, session: Session, *, runtime: UserModelRuntime | None = None) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._states = UserStateRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._tasks = TaskRepository(session)
        self._feedbacks = FeedbackRepository(session)
        self._goals = GoalRepository(session)
        self._daily_states = DailyStateRepository(session)
        self._prediction_snapshots = PredictionSnapshotRepository(session)
        self._prediction_outcomes = PredictionOutcomeRepository(session)
        self._shadow = ShadowPredictionRepository(session)
        self._synthetic = SyntheticDataRepository(session)
        if runtime is None:
            from app.application.services.model_runtime import get_user_model_runtime

            runtime = get_user_model_runtime()
        self._runtime = runtime

    @property
    def runtime(self) -> UserModelRuntime:
        return self._runtime

    # ------------------------------------------------------------------
    # Level 1
    # ------------------------------------------------------------------
    def get_trait_profile(self, user_id: int) -> dict[str, Any] | None:
        user = self._users.get_by_id(user_id)
        return dict(user.trait_profile) if user and user.trait_profile else None

    def set_trait_profile(self, user_id: int, profile: dict[str, Any]) -> dict[str, Any]:
        """Validate a Level 1 profile through the real model and persist it."""
        from app.application.exceptions import NotFoundError

        if self._users.get_by_id(user_id) is None:
            raise NotFoundError("user not found")
        validated = self._runtime.level1.validate_profile(profile)
        payload = validated.model_dump(mode="json")
        meta = self._runtime.level1.metadata
        self._users.update_fields(
            user_id,
            trait_profile=payload,
            trait_model_version=meta.model_version,
            trait_artifact_hash=meta.artifact_hash,
            trait_feature_version=meta.feature_version,
        )
        return payload

    # ------------------------------------------------------------------
    # Level 2
    # ------------------------------------------------------------------
    def get_state_profile(self, user_id: int) -> dict[str, Any] | None:
        row = self._states.get_by_user(user_id)
        return dict(row.level2_profile) if row and row.level2_profile else None

    def refresh_dynamic_state(
        self, user_id: int, *, commit: bool = True
    ) -> DynamicStateSnapshot | None:
        """Replay Level 2 over the user's real history and persist the state."""
        trait = self.get_trait_profile(user_id)
        if trait is None:
            return None
        days, day_origins = self._build_days_with_origins(user_id)
        if not days:
            return None
        try:
            profiles = self._runtime.level2.replay_all(days, trait)
            snapshots = [self._runtime.level2.snapshot(profile) for profile in profiles]
        except Exception as exc:  # noqa: BLE001 - Level 2 failure must degrade
            logger.warning("level2 refresh failed for user=%s: %s", user_id, exc)
            return None

        snapshot = snapshots[-1]
        cutoff = date.today() - timedelta(days=get_settings().daily_state_retention_days)
        try:
            # Savepoint: a failed audit write must not poison the caller's unit
            # of work (this runs inside planning / profile requests).
            with self._session.begin_nested():
                for daily_snapshot in snapshots:
                    if daily_snapshot.date < cutoff:
                        # Still replayed (state depends on the full history) but
                        # not worth persisting just to be pruned right after.
                        continue
                    availability, evidence_count, conflict = _evidence_summary(daily_snapshot)
                    self._daily_states.upsert(
                        DailyState(
                            user_id=user_id,
                            date=daily_snapshot.date,
                            fatigue=round(daily_snapshot.fatigue.value, 6),
                            stress=round(daily_snapshot.stress.value, 6),
                            self_efficacy=round(daily_snapshot.self_efficacy.value, 6),
                            fatigue_uncertainty=round(daily_snapshot.fatigue.uncertainty, 6),
                            stress_uncertainty=round(daily_snapshot.stress.uncertainty, 6),
                            self_efficacy_uncertainty=round(
                                daily_snapshot.self_efficacy.uncertainty, 6
                            ),
                            evidence_availability=availability,
                            evidence_count=evidence_count,
                            conflict=conflict,
                            next_day_prior=daily_snapshot.next_day_prior or None,
                            next_day_uncertainty=daily_snapshot.next_day_uncertainty or None,
                            cold_start=daily_snapshot.cold_start,
                            gap_days=daily_snapshot.gap_days,
                            profile_json=daily_snapshot.profile_json,
                            model_version=daily_snapshot.model_version,
                            config_version=daily_snapshot.config_version,
                            artifact_hash=daily_snapshot.metadata.artifact_hash,
                            # Provenance of the observations behind that day, not
                            # a user-global flag: a real day stays 'real'.
                            data_origin=day_origins.get(daily_snapshot.date, "real"),
                        )
                    )
                self._daily_states.prune_before(user_id, cutoff)
        except Exception as exc:  # noqa: BLE001 - audit history must degrade
            logger.warning(
                "daily state persistence failed for user=%s: %s", user_id, exc
            )

        existing = self._states.get_by_user(user_id) or UserStateData()
        updated = replace(
            existing,
            state_fatigue=round(snapshot.fatigue.value, 6),
            state_stress=round(snapshot.stress.value, 6),
            self_efficacy=round(snapshot.self_efficacy.value, 6),
            state_fatigue_uncertainty=round(snapshot.fatigue.uncertainty, 6),
            state_stress_uncertainty=round(snapshot.stress.uncertainty, 6),
            self_efficacy_uncertainty=round(snapshot.self_efficacy.uncertainty, 6),
            # Legacy display projection only (0..1 energy); the authoritative
            # value is ``state_fatigue`` / the Level 2 snapshot.
            state_energy=round(max(0.0, min(1.0, 1.0 - snapshot.fatigue.value)), 6),
            stress_baseline=round(snapshot.stress.value, 6),
            update_count=len(days),
            level2_profile=snapshot.profile_json,
            level2_profile_date=snapshot.date,
            level2_model_version=snapshot.model_version,
            level2_config_version=snapshot.config_version,
            level2_artifact_hash=snapshot.metadata.artifact_hash,
            level2_updated_at=datetime.now(UTC),
        )
        self._states.upsert(user_id, updated)
        if commit:
            self._session.commit()
        return snapshot

    def build_days(self, user_id: int) -> list[DayInput]:
        return self._build_days(user_id)

    def _build_days(self, user_id: int) -> list[DayInput]:
        return self._build_days_with_origins(user_id)[0]

    def _build_days_with_origins(
        self, user_id: int
    ) -> tuple[list[DayInput], dict[date, str]]:
        """Build Level 2 day inputs plus the per-day provenance of their data."""
        tasks = self._tasks.list_by_user(user_id)
        executions = self._executions.list_by_user(user_id, limit=2000)
        feedbacks = self._feedbacks.list_by_user(user_id, limit=500)
        task_by_id = {task.id: task for task in tasks if task.id is not None}
        goal_deadlines = {
            goal.id: _as_deadline_naive(goal.deadline)
            for goal in self._goals.list_by_user(user_id)
            if goal.id is not None and goal.deadline is not None
        }
        today = date.today()

        buckets: dict[date, dict[str, list]] = {}

        def bucket(day: date) -> dict[str, list]:
            return buckets.setdefault(day, {"tasks": [], "executions": []})

        for task in tasks:
            day = task.scheduled_date or task.occurrence_date
            if day is None or day > today:
                continue
            entry = bucket(day)
            if task not in entry["tasks"]:
                entry["tasks"].append(task)

        for execution in executions:
            # A "start only" row (started_at, no finish/completion/rate) exists
            # so the start time is auditable. It must not count as a failed task
            # in Level 2/3 history.
            if not _is_observed_execution(execution):
                continue
            task = task_by_id.get(execution.task_id)
            day = None
            if task is not None:
                day = task.scheduled_date or task.occurrence_date
            if day is None and execution.created_at is not None:
                day = execution.created_at.date()
            if day is None or day > today:
                continue
            entry = bucket(day)
            if task is not None and task not in entry["tasks"]:
                entry["tasks"].append(task)
            entry["executions"].append(execution)

        feedback_by_day = {feedback.date: feedback for feedback in feedbacks}
        for day in feedback_by_day:
            if day <= today:
                bucket(day)

        origins: dict[date, str] = {}

        def mark_origin(day: date, origin: str) -> None:
            # A day is synthetic if any observation behind it is synthetic;
            # an empty cold-start day is real.
            if origins.get(day) == "synthetic" or origin == "synthetic":
                origins[day] = "synthetic"
            else:
                origins.setdefault(day, "real")

        for day, entry in buckets.items():
            for task in entry["tasks"]:
                mark_origin(day, task.data_origin)
            for execution in entry["executions"]:
                mark_origin(day, execution.data_origin)
            feedback = feedback_by_day.get(day)
            if feedback is not None:
                mark_origin(day, feedback.data_origin)

        days: list[DayInput] = []
        for day in sorted(buckets):
            entry = buckets[day]
            plans = [
                self._level2_task_plan(
                    task,
                    day,
                    goal_deadlines.get(task.goal_id) if task.goal_id is not None else None,
                )
                for task in entry["tasks"]
            ]
            known_ids = {plan.task_id for plan in plans}
            # One task can have several execution rows on the same day: the
            # frontend patches start, partial progress and completion
            # separately, and each patch appends a row. Level 2 requires one
            # execution per task/day, so collapse them chronologically first.
            grouped: dict[int, list[TaskExecution]] = {}
            for execution in entry["executions"]:
                if str(execution.task_id) not in known_ids:
                    continue
                grouped.setdefault(execution.task_id, []).append(execution)
            day_executions = [
                self._level2_execution(self._merge_executions(grouped[task_id]))
                for task_id in sorted(grouped)
            ]
            feedback = feedback_by_day.get(day)
            reflection = None
            passive = None
            if feedback is not None:
                fallback = (feedback.free_text or feedback.delay_reason or "").strip() or None
                candidate = ReflectionInput(
                    day_review=feedback.day_review or fallback,
                    stuck_points=feedback.stuck_points,
                    state_review=feedback.state_review,
                    tomorrow_outlook=feedback.tomorrow_outlook,
                )
                if not candidate.is_empty():
                    reflection = candidate
                if feedback.sleep_hours is not None:
                    passive = PassiveContext(
                        sleep_duration_minutes=float(feedback.sleep_hours) * 60.0
                    )
            if not plans and not day_executions and reflection is None:
                continue
            days.append(
                DayInput(
                    date=day,
                    task_plans=plans,
                    task_executions=day_executions,
                    reflection=reflection,
                    passive_context=passive,
                )
            )
        return days, origins

    @staticmethod
    def _merge_executions(rows: list[TaskExecution]) -> TaskExecution:
        """Collapse one task/day's execution rows into a single observation.

        The frontend patches start, partial progress and completion separately;
        each patch appends a row. Level 2 models one execution per task/day, so
        collapse the rows chronologically: earliest start, latest finish, latest
        cumulative duration, maximum completion, latest observed interruptions.
        """
        if not rows:
            raise ValueError("cannot merge an empty list of executions")
        ordered = sorted(rows, key=lambda row: (row.created_at, row.id or 0))
        started_at: datetime | None = None
        finished_at: datetime | None = None
        actual_duration: int | None = None
        completion_rate = 0.0
        completed = False
        interruption_count: int | None = None
        metadata: dict[str, Any] = {}
        for row in ordered:
            if row.started_at is not None:
                started_at = (
                    row.started_at
                    if started_at is None
                    else min(started_at, row.started_at)
                )
            if row.finished_at is not None:
                finished_at = (
                    row.finished_at
                    if finished_at is None
                    else max(finished_at, row.finished_at)
                )
            if row.actual_duration is not None:
                # The frontend sends cumulative actual minutes, not increments.
                actual_duration = row.actual_duration
            completion_rate = max(completion_rate, row.completion_rate)
            completed = completed or row.completed
            if row.interruption_count is not None:
                interruption_count = row.interruption_count
            for field in (
                "difficulty_feedback",
                "stress_before",
                "stress_after",
                "failure_reason",
                "time_of_day",
            ):
                value = getattr(row, field)
                if value is not None:
                    metadata[field] = value
        latest = ordered[-1]
        return latest.model_copy(
            update={
                "started_at": started_at,
                "finished_at": finished_at,
                "actual_duration": actual_duration,
                "completion_rate": completion_rate,
                "completed": completed,
                "interruption_count": interruption_count,
                # Non-null in the domain model: keep the latest row's values.
                "planned_duration": latest.planned_duration,
                "data_origin": latest.data_origin,
                "created_at": latest.created_at,
                **metadata,
            }
        )

    @staticmethod
    def _level2_task_plan(
        task: Task,
        day: date,
        goal_deadline: datetime | None = None,
    ) -> Level2TaskPlan:
        start = datetime.combine(day, task.start_time or DEFAULT_DAY_START)
        deadline = _as_deadline_naive(task.deadline) or goal_deadline
        # TaskPlan rejects a deadline before the planned start; omit it instead
        # of failing the whole replay for one inconsistent historical row.
        if deadline is not None and deadline < start:
            deadline = None
        return Level2TaskPlan(
            task_id=str(task.id),
            title=task.title,
            planned_start=start,
            estimated_duration_minutes=max(int(task.estimated_duration), 1),
            deadline=deadline,
            difficulty=task.difficulty,
        )

    @staticmethod
    def _level2_execution(execution) -> Level2TaskExecution:
        return Level2TaskExecution(
            task_id=str(execution.task_id),
            actual_start=execution.started_at,
            actual_duration_minutes=execution.actual_duration,
            completion_ratio=execution.completion_rate,
            completed=bool(execution.completed),
            interruption_count=execution.interruption_count,
        )

    # ------------------------------------------------------------------
    # Typed context / history
    # ------------------------------------------------------------------
    def has_synthetic_observations(self, user_id: int) -> bool:
        return self._synthetic.has_synthetic(user_id)

    def build_history(self, user_id: int) -> HistoryBundle:
        executions = [
            execution
            for execution in reversed(
                self._executions.list_by_user(user_id, limit=500)
            )
            if _is_observed_execution(execution)
        ]
        completion = [bool(execution.completed) for execution in executions]
        ratios = [
            round(execution.actual_duration / execution.planned_duration, 6)
            for execution in executions
            if execution.actual_duration and execution.planned_duration
        ]
        feedbacks = list(reversed(self._feedbacks.list_by_user(user_id, limit=30)))
        recent = feedbacks[-7:]
        goal = round(mean(f.completion_rate for f in recent), 6) if recent else None
        completed = sum(completion)
        return HistoryBundle(
            completion_history=completion,
            duration_ratio_history=ratios,
            similar_duration_ratio_history=[],
            total_historical_tasks=len(executions),
            completed_task_count=completed,
            failed_task_count=len(completion) - completed,
            usable_duration_samples=len(ratios),
            similar_task_sample_count=0,
            similar_task_type=None,
            recent_goal_attainment=goal,
        )

    def context(self, user_id: int) -> UserModelContext:
        trait_profile = self.get_trait_profile(user_id)
        state_profile = self.get_state_profile(user_id)
        if trait_profile is not None and state_profile is None:
            # First run after the feature was deployed: derive Level 2 from the
            # real history once, then reuse the persisted snapshot.
            snapshot = self.refresh_dynamic_state(user_id)
            state_profile = snapshot.profile_json if snapshot is not None else None
        return self._runtime.build_context(
            trait_profile=trait_profile,
            state_profile=state_profile,
            history=self.build_history(user_id),
        )

    def task_context(
        self,
        task: Task,
        *,
        task_type: str | None = None,
        available_minutes: float | None = None,
    ) -> TaskPredictionContext:
        start = None
        if task.scheduled_date is not None:
            start = datetime.combine(task.scheduled_date, task.start_time or DEFAULT_DAY_START)
        deadline = _as_deadline_utc(task.deadline)
        if deadline is None and task.goal_id is not None:
            goal = self._goals.get_by_id(task.goal_id)
            if goal is not None:
                deadline = _as_deadline_utc(goal.deadline)
        return TaskPredictionContext(
            task_id=str(task.id or 0),
            title=task.title,
            estimated_duration_minutes=float(task.predicted_duration or task.estimated_duration),
            difficulty=task.difficulty,
            deadline=deadline,
            planned_start=start,
            task_type=task_type if task_type is not None else task.task_type,
            available_time_minutes=available_minutes,
            time_of_day=start.hour if start else datetime.now().hour,
        )

    # ------------------------------------------------------------------
    # Level 3 shadow
    # ------------------------------------------------------------------
    def run_shadow_for_plan(
        self,
        *,
        user_id: int,
        plan_id: int | None,
        tasks: list[Task],
        context: UserModelContext | None = None,
        data_origin: str = "real",
    ) -> int:
        """Run Level 3 for each task and persist audit rows. Never raises."""
        if self._runtime.mode is Level3Mode.OFF:
            return 0
        ctx = context or self.context(user_id)
        runner = Level3ShadowRunner(self._runtime)
        written = 0
        for task in tasks:
            if task.id is None:
                continue
            production = {
                "predicted_duration": task.predicted_duration,
                "completion_probability": task.completion_probability,
                "scheduled_date": task.scheduled_date.isoformat()
                if task.scheduled_date
                else None,
                "start_time": task.start_time.isoformat() if task.start_time else None,
                "prediction_source": task.prediction_source,
            }
            record: ShadowPredictionRecord | None
            if ctx.trait is None or ctx.state is None or ctx.history is None:
                missing = []
                if ctx.trait is None:
                    missing.append("level1_unavailable")
                if ctx.state is None:
                    missing.append("level2_unavailable")
                if ctx.history is None:
                    missing.append("history_unavailable")
                record = self._failed_record(
                    user_id=user_id,
                    plan_id=plan_id,
                    task=task,
                    production=production,
                    reason=",".join(missing),
                    mode=self._runtime.mode.value,
                    data_origin=data_origin,
                )
            else:
                record = runner.run(
                    user_id=user_id,
                    plan_id=plan_id,
                    task_id=task.id,
                    trait=ctx.trait,
                    state=ctx.state,
                    history=ctx.history,
                    task=self.task_context(task),
                    production_decision=production,
                    data_origin=data_origin,
                )
            if record is None:
                continue
            try:
                from app.domain.models.shadow_prediction import ShadowPrediction

                # Savepoint: one failed audit row must not poison the session.
                with self._session.begin_nested():
                    self._shadow.create(
                        ShadowPrediction(**record.model_dump(exclude={"feature_snapshot"}))
                    )
                written += 1
            except Exception as exc:  # noqa: BLE001 - audit failure is not a plan failure
                logger.warning("failed to persist shadow prediction: %s", exc)
            if record.success and record.feature_snapshot:
                self._persist_prediction_snapshot(
                    user_id=user_id,
                    plan_id=plan_id,
                    task=task,
                    record=record,
                    ctx=ctx,
                    production=production,
                    data_origin=data_origin,
                )
        return written

    def _persist_prediction_snapshot(
        self,
        *,
        user_id: int,
        plan_id: int | None,
        task: Task,
        record: ShadowPredictionRecord,
        ctx: UserModelContext,
        production: dict[str, Any],
        data_origin: str,
    ) -> None:
        """Freeze the Level 3 inputs at prediction time (audit only, never raises)."""
        if task.id is None or ctx.trait is None or ctx.state is None or ctx.history is None:
            return
        meta = self._runtime.level3.metadata
        try:
            with self._session.begin_nested():
                self._prediction_snapshots.create(
                    PredictionSnapshot(
                    user_id=user_id,
                    task_id=task.id,
                    plan_id=plan_id,
                    prediction_timestamp=record.inference_timestamp,
                    trait=ctx.trait.model_dump(mode="json"),
                    state=ctx.state.model_dump(mode="json"),
                    history=ctx.history.model_dump(mode="json"),
                    task=self.task_context(task).model_dump(mode="json"),
                    context=dict(production),
                    feature_snapshot=record.feature_snapshot,
                    input_hash=record.input_hash,
                    model_version=record.model_version or meta.model_version,
                    # Recallable model configuration (falls back to the artifact
                    # version if the runtime is unavailable).
                    config_version=_level3_config_version(self._runtime),
                    artifact_hash=meta.artifact_hash,
                    mode=record.mode,
                    data_origin=data_origin,
                )
                )
        except Exception as exc:  # noqa: BLE001 - audit failure is not a plan failure
            logger.warning(
                "failed to persist prediction snapshot for task=%s: %s",
                task.id,
                exc,
            )

    def record_prediction_outcome(
        self, user_id: int, task_id: int
    ) -> PredictionOutcome | None:
        """Attach the latest observed execution to the newest unlabelled snapshot.

        Best effort: this feeds evaluation later and must never break task
        execution, so every failure is contained.
        """
        try:
            execution = None
            for candidate in self._executions.list_by_task(task_id):
                if _is_observed_execution(candidate):
                    execution = candidate
            if execution is None:
                return None
            execution_time = _to_utc_aware(execution.finished_at or execution.created_at)

            snapshot = None
            for candidate in self._prediction_snapshots.list_by_task(task_id):
                if candidate.user_id != user_id or candidate.id is None:
                    continue
                if self._prediction_outcomes.get_by_snapshot(candidate.id) is not None:
                    continue
                predicted_at = _to_utc_aware(candidate.prediction_timestamp)
                if execution_time is not None and predicted_at is not None:
                    if predicted_at > execution_time:
                        # Never label an earlier prediction with a later run.
                        continue
                snapshot = candidate
                break
            if snapshot is None or snapshot.id is None:
                return None
            return self._prediction_outcomes.create(
                PredictionOutcome(
                    snapshot_id=snapshot.id,
                    task_id=task_id,
                    completed=bool(execution.completed),
                    completion_ratio=execution.completion_rate,
                    actual_duration_minutes=(
                        float(execution.actual_duration)
                        if execution.actual_duration is not None
                        else None
                    ),
                    outcome_timestamp=execution.finished_at or execution.created_at,
                    notes=execution.failure_reason,
                    source="execution",
                )
            )
        except Exception as exc:  # noqa: BLE001 - callers treat this as best effort
            logger.warning(
                "failed to record prediction outcome for user=%s task=%s: %s",
                user_id,
                task_id,
                exc,
            )
            return None

    def _failed_record(
        self,
        *,
        user_id: int,
        plan_id: int | None,
        task: Task,
        production: dict[str, Any],
        reason: str,
        mode: str,
        data_origin: str = "real",
    ) -> ShadowPredictionRecord:
        meta = self._runtime.level3.metadata
        return ShadowPredictionRecord(
            user_id=user_id,
            plan_id=plan_id,
            task_id=task.id,
            inference_timestamp=datetime.now(UTC),
            model_version=meta.model_version,
            artifact_hash=meta.artifact_hash,
            artifact_version=meta.artifact_version,
            feature_version=meta.feature_version,
            production_decision=production,
            success=False,
            failure_reason=reason[:500],
            degraded=True,
            mode=mode,
            data_origin=data_origin,
        )

    def latest_shadow(self, user_id: int, *, limit: int = 20):
        return self._shadow.list_by_user(user_id, limit=limit)

    def shadow_summary(self, user_id: int) -> dict[str, Any]:
        rows = self._shadow.list_by_user(user_id, limit=500)
        if not rows:
            return {
                "runs": 0,
                "success_rate": None,
                "failures": 0,
                "mean_disagreement": None,
                "status": "no_runtime_data",
            }
        successful = [row for row in rows if row.success]
        disagreements = [
            row.disagreement for row in rows if row.disagreement is not None
        ]
        return {
            "runs": len(rows),
            "success_rate": round(len(successful) / len(rows), 4),
            "failures": len(rows) - len(successful),
            "mean_disagreement": (
                round(mean(disagreements), 6) if disagreements else None
            ),
            "status": "ok",
        }

    def describe(self) -> dict[str, Any]:
        return self._runtime.describe()


__all__ = ["DEFAULT_DAY_START", "UserModelService"]
