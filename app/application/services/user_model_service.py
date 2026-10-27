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
from datetime import UTC, date, datetime, time
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from app.domain.models import Task, TaskExecution
from app.domain.profile.models import UserStateData
from app.infrastructure.database.repositories import (
    FeedbackRepository,
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


class UserModelService:
    def __init__(self, session: Session, *, runtime: UserModelRuntime | None = None) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._states = UserStateRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._tasks = TaskRepository(session)
        self._feedbacks = FeedbackRepository(session)
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
        days = self._build_days(user_id)
        if not days:
            return None
        try:
            profile = self._runtime.level2.replay(days, trait)
            snapshot = self._runtime.level2.snapshot(profile)
        except Exception as exc:  # noqa: BLE001 - Level 2 failure must degrade
            logger.warning("level2 refresh failed for user=%s: %s", user_id, exc)
            return None

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
        tasks = self._tasks.list_by_user(user_id)
        executions = self._executions.list_by_user(user_id, limit=2000)
        feedbacks = self._feedbacks.list_by_user(user_id, limit=500)
        task_by_id = {task.id: task for task in tasks if task.id is not None}
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
            # A task can be scheduled for tomorrow but completed early today.
            # Prefer the observed execution date over dropping the observation.
            if day is None or day > today:
                if execution.created_at is not None:
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

        days: list[DayInput] = []
        for day in sorted(buckets):
            entry = buckets[day]
            plans = [self._level2_task_plan(task, day) for task in entry["tasks"]]
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
                text = (feedback.free_text or feedback.delay_reason or "").strip()
                if text:
                    reflection = ReflectionInput(day_review=text)
                if feedback.sleep_hours is not None:
                    passive = PassiveContext(
                        sleep_duration_minutes=float(feedback.sleep_hours) * 60.0
                    )
            if not plans and not day_executions and reflection is None and feedback is None:
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
        return days

    @staticmethod
    def _merge_executions(rows: list[TaskExecution]) -> TaskExecution:
        """Collapse one task/day's execution rows into a single observation.

        ``PlanService.update_task`` appends a row per execution patch (start,
        partial progress, completion). Level 2 models one execution per task and
        day, so the rows are merged chronologically: earliest start, latest
        finish, latest cumulative duration, maximum completion and the latest
        observed interruption count (``None`` stays ``None``).
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
    def _level2_task_plan(task: Task, day: date) -> Level2TaskPlan:
        start = datetime.combine(day, task.start_time or DEFAULT_DAY_START)
        return Level2TaskPlan(
            task_id=str(task.id),
            title=task.title,
            planned_start=start,
            estimated_duration_minutes=max(int(task.estimated_duration), 1),
            deadline=None,
            difficulty=None,
        )

    @staticmethod
    def _level2_execution(execution) -> Level2TaskExecution:
        # TaskPlan.planned_start is local-naive; PostgreSQL returns TIMESTAMPTZ
        # values with the session timezone. Normalise to local-naive so the
        # DDSR delay comparison uses the same clock as the plan.
        actual_start = execution.started_at
        if actual_start is not None and actual_start.tzinfo is not None:
            actual_start = actual_start.astimezone().replace(tzinfo=None)
        return Level2TaskExecution(
            task_id=str(execution.task_id),
            actual_start=actual_start,
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
        return TaskPredictionContext(
            task_id=str(task.id or 0),
            title=task.title,
            estimated_duration_minutes=float(task.predicted_duration or task.estimated_duration),
            difficulty=None,
            deadline=None,
            planned_start=start,
            task_type=task_type,
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

                self._shadow.create(ShadowPrediction(**record.model_dump()))
                written += 1
            except Exception as exc:  # noqa: BLE001 - audit failure is not a plan failure
                logger.warning("failed to persist shadow prediction: %s", exc)
        return written

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