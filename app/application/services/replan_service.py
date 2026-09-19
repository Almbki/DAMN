"""Replan service: eligibility (cooldown) + versioned replanning.

Replanning never overwrites a plan: it creates a new ``Plan`` version, copies
the still-relevant tasks with a fresh schedule, marks the previous version as
``SUPERSEDED`` and records a :class:`ReplanEvent` explaining the change.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.application.dto.replan import ReplanEligibility, ReplanResult
from app.application.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ReplanNotEligibleError,
)
from app.core.config import get_settings
from app.domain.models import Plan, ReplanEvent, Task
from app.domain.models.enums import (
    PlanStatus,
    ReplanTriggerType,
    TaskStatus,
)
from app.domain.rules.base import RuleContext, RuleEngine
from app.domain.scheduling.scheduler import Scheduler
from app.infrastructure.database.repositories import (
    GoalRepository,
    PlanRepository,
    ReplanEventRepository,
    TaskRepository,
)


class ReplanService:
    def __init__(
        self,
        session: Session,
        *,
        scheduler: Scheduler | None = None,
        rule_engine: RuleEngine | None = None,
    ) -> None:
        self._session = session
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)
        self._goals = GoalRepository(session)
        self._events = ReplanEventRepository(session)
        self._scheduler = scheduler or Scheduler()
        self._rule_engine = rule_engine or RuleEngine()
        self._settings = get_settings()

    # -- eligibility -------------------------------------------------------
    def check_eligibility(self, user_id: int, plan_id: int) -> ReplanEligibility:
        # Raises NotFoundError / PermissionDeniedError for unknown or foreign plans.
        self._require_plan(user_id, plan_id)
        # Cooldown is a per-user rate limit: after any replan, no further replan
        # is allowed until the cooldown elapses (regardless of plan version).
        latest = self._events.get_latest_for_user(user_id)
        cooldown = self._settings.scheduler_min_replan_interval_hours
        if latest is None or latest.created_at is None:
            return ReplanEligibility(
                eligible=True, reason="no previous replan", cooldown_hours=cooldown
            )

        last_at = latest.created_at
        if last_at.tzinfo is None:  # sqlite may return naive datetimes
            last_at = last_at.replace(tzinfo=UTC)
        next_at = last_at + timedelta(hours=cooldown)
        now = datetime.now(UTC)
        if now >= next_at:
            return ReplanEligibility(
                eligible=True,
                reason="cooldown elapsed",
                last_replan_at=last_at,
                next_eligible_at=next_at,
                cooldown_hours=cooldown,
            )
        return ReplanEligibility(
            eligible=False,
            reason=f"cooldown active until {next_at.isoformat()}",
            last_replan_at=last_at,
            next_eligible_at=next_at,
            cooldown_hours=cooldown,
        )

    # -- replan ------------------------------------------------------------
    def replan(
        self,
        user_id: int,
        plan_id: int,
        *,
        reason: str | None = None,
        trigger_type: ReplanTriggerType = ReplanTriggerType.MANUAL,
        from_date: date | None = None,
    ) -> ReplanResult:
        eligibility = self.check_eligibility(user_id, plan_id)
        if not eligibility.eligible:
            raise ReplanNotEligibleError(eligibility.reason, detail=eligibility.model_dump())

        old_plan = self._require_plan(user_id, plan_id)
        old_tasks = self._tasks.list_by_plan(plan_id)
        pending = [
            task
            for task in old_tasks
            if task.status not in {TaskStatus.COMPLETED, TaskStatus.SKIPPED}
        ]

        context = self._build_context(pending, user_id)
        tasks_for_scheduler = [
            task.model_copy(update={"plan_id": old_plan.id or plan_id}) for task in pending
        ]
        schedule = self._scheduler.schedule(tasks_for_scheduler, context)
        schedule_map = {item.task_id: item for item in schedule.tasks}

        new_plan = Plan(
            user_id=user_id,
            version=self._plans.next_version(user_id),
            status=PlanStatus.ACTIVE,
            title=old_plan.title,
            start_date=from_date or old_plan.start_date,
            end_date=old_plan.end_date,
            parent_plan_id=old_plan.id,
            confidence=old_plan.confidence,
        )
        new_plan = self._plans.create(new_plan)

        changed: list[int] = []
        new_tasks: list[Task] = []
        for task in pending:
            placed = schedule_map.get(task.id)
            scheduled_date = placed.scheduled_date if placed else None
            start_time = placed.start_time if placed else None
            end_time = placed.end_time if placed else None
            if (scheduled_date, start_time, end_time) != (
                task.scheduled_date,
                task.start_time,
                task.end_time,
            ):
                changed.append(task.id or 0)
            new_tasks.append(
                task.model_copy(
                    update={
                        "id": None,
                        "plan_id": new_plan.id,
                        "scheduled_date": scheduled_date,
                        "start_time": start_time,
                        "end_time": end_time,
                        "status": TaskStatus.SCHEDULED,
                    }
                )
            )
        if new_tasks:
            self._tasks.create_many(new_tasks)

        self._plans.update_status(plan_id, PlanStatus.SUPERSEDED)
        event = ReplanEvent(
            plan_id=new_plan.id or plan_id,
            trigger_type=trigger_type,
            reason=reason or "replanned",
            old_version=old_plan.version,
            new_version=new_plan.version,
            changed_tasks=[task_id for task_id in changed if task_id],
        )
        self._events.create(event)
        self._session.commit()

        return ReplanResult(
            plan=new_plan,
            old_version=old_plan.version,
            new_version=new_plan.version,
            changed_task_ids=event.changed_tasks,
            reason=event.reason or "",
            trigger_type=trigger_type,
        )

    # -- helpers -----------------------------------------------------------
    def _require_plan(self, user_id: int, plan_id: int) -> Plan:
        plan = self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError("plan not found")
        if plan.user_id != user_id:
            raise PermissionDeniedError("plan belongs to another user")
        return plan

    def _build_context(self, tasks: list[Task], user_id: int) -> RuleContext:
        goal_ids = [t.goal_id for t in tasks if t.goal_id is not None]
        goals = self._goals.list_by_ids(list(set(goal_ids))) if goal_ids else []
        deadlines = {
            task.id: goal.deadline.date()
            for task in tasks
            for goal in goals
            if task.goal_id == goal.id and goal.deadline is not None and task.id is not None
        }
        return RuleContext(
            daily_limit_minutes=self._settings.scheduler_daily_limit_minutes,
            buffer_minutes=self._settings.scheduler_buffer_minutes,
            high_cognitive_max_per_day=self._settings.scheduler_high_cognitive_max_per_day,
            available_minutes_per_day=max(
                self._settings.scheduler_daily_limit_minutes,
                self._settings.scheduler_daily_limit_minutes,
            ),
            task_deadlines=deadlines,
            completed_task_ids={
                t.id for t in tasks if t.status == TaskStatus.COMPLETED and t.id is not None
            },
        )
