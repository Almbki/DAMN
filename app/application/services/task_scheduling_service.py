"""Deterministic execution-time scheduling commands.

Three LLM-free mutations on a confirmed active plan:

* ``move_task_to_backlog`` - keep the task but clear its placement.
* ``move_task``            - coarse drag placement (30-minute grid).
* ``local_reschedule``     - re-place a work-unit sequence from a chosen node.

All three reuse the existing Scheduler / RuleEngine. The task detail PATCH path
calls :meth:`validate_placement` too, so precise edits and drag edits share one
hard-constraint pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta

from sqlalchemy.orm import Session

from app.application.exceptions import (
    ConflictError,
    DomainValidationError,
    NotFoundError,
    PermissionDeniedError,
)
from app.application.preferences import effective_scheduling_preferences
from app.core.clock import local_now, local_today
from app.domain.date_constraints import resolve_earliest_start
from app.domain.models import Goal, Plan, Task
from app.domain.models.enums import PlanStatus, TaskStatus
from app.domain.rules.base import RuleContext, RuleEngine, RuleViolation
from app.domain.scheduling.fixed_events import expand_fixed_events
from app.domain.scheduling.placement import (
    add_minutes,
    snap_time_to_grid,
    time_to_minutes,
)
from app.domain.scheduling.schedule_result import (
    CandidateSchedule,
    FixedEvent,
    ScheduledTask,
)
from app.domain.scheduling.scheduler import Scheduler
from app.infrastructure.database.repositories import (
    GoalRepository,
    PlanRepository,
    ScheduleEventRepository,
    TaskRepository,
    UserRepository,
)

DEFAULT_DAY_START = time(8, 0)
DEFAULT_DAY_END = time(22, 0)
_HORIZON_DAYS = 13

#: Statuses that may be dragged or put into the backlog.
_MOVABLE_STATUSES = frozenset(
    {
        TaskStatus.PENDING,
        TaskStatus.SCHEDULED,
        TaskStatus.IN_PROGRESS,
        TaskStatus.OVERDUE,
        TaskStatus.BACKLOG,
    }
)
_BACKLOG_STATUSES = frozenset(
    {TaskStatus.PENDING, TaskStatus.SCHEDULED, TaskStatus.OVERDUE, TaskStatus.BACKLOG}
)
_NON_MOVABLE_STATUSES = frozenset(
    {
        TaskStatus.COMPLETED,
        TaskStatus.SKIPPED,
        TaskStatus.MISSED,
        TaskStatus.FAILED,
    }
)

_REASON_TEXT = {
    "fixed_event_overlap": "与固定日程冲突",
    "daily_limit": "当天任务总量超过上限",
    "available_time": "当天可用时间不足",
    "outside_available_window": "超出可安排时间窗",
    "GOAL_DAILY_CAPACITY_EXCEEDED": "该目标今天已达到每日时长上限",
    "goal_daily_capacity": "该目标今天已达到每日时长上限",
    "insufficient_buffer": "与相邻任务的缓冲时间不足",
    "deadline_exceeded": "安排日期超过了截止时间",
    "earliest_start": "安排日期早于最早开始日期",
    "high_cognitive_consecutive": "高认知任务之间间隔不足",
    "high_cognitive_daily_max": "当天高认知任务已达上限",
    "same_day_conflict": "当天存在冲突科目",
    "recurrence_wrong_day": "重复任务不能移动到其他日期",
    "completed_task_rescheduled": "已完成任务不能移动",
}


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


def _duration(task: Task) -> int:
    return max(1, int(task.predicted_duration or task.estimated_duration))


def _reason_text(violation: RuleViolation) -> str:
    code = violation.code or violation.rule
    return _REASON_TEXT.get(code, violation.message or "安排不合法")


@dataclass
class _PlacementContext:
    plan: Plan
    task: Task
    tasks: list[Task]
    goals: dict[int, Goal]
    rule_context: RuleContext
    today: date
    now_time: time


class TaskSchedulingService:
    """Owns Backlog / MOVE / LOCAL_RESCHEDULE. Never calls an LLM."""

    def __init__(
        self,
        session: Session,
        *,
        scheduler: Scheduler | None = None,
        rule_engine: RuleEngine | None = None,
    ) -> None:
        self._session = session
        self._tasks = TaskRepository(session)
        self._plans = PlanRepository(session)
        self._goals = GoalRepository(session)
        self._users = UserRepository(session)
        self._events = ScheduleEventRepository(session)
        self._scheduler = scheduler or Scheduler()
        self._rules = rule_engine or RuleEngine()

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    def move_task_to_backlog(
        self, user_id: int, plan_id: int, task_id: int
    ) -> Task:
        ctx = self._load(user_id, plan_id, task_id)
        task = ctx.task
        if task.status == TaskStatus.BACKLOG:
            return task
        self._assert_backloggable(ctx)
        updated = self._tasks.update_fields(
            task.id,
            scheduled_date=None,
            start_time=None,
            end_time=None,
            status=TaskStatus.BACKLOG,
            scheduling_reason=None,
            scheduling_detail=None,
        )
        self._session.commit()
        return updated or task

    def move_task(
        self,
        user_id: int,
        plan_id: int,
        task_id: int,
        *,
        target_date: date,
        target_start: time,
        snap: bool = True,
    ) -> Task:
        ctx = self._load(user_id, plan_id, task_id, extra_end=target_date)
        self._assert_movable(ctx.task)
        start = snap_time_to_grid(target_start) if snap else target_start
        duration = _duration(ctx.task)
        if time_to_minutes(start) + duration > 24 * 60:
            raise DomainValidationError(
                "任务结束时间超过了当天 24:00",
                detail={"reason_code": "OUTSIDE_AVAILABLE_WINDOW"},
            )
        end = add_minutes(start, duration)
        self._validate_target_day(ctx, target_date, start, enforce_now=True)
        self._validate_placement(
            ctx, ctx.task, target_date, start, end, duration
        )
        updated = self._tasks.update_fields(
            ctx.task.id,
            scheduled_date=target_date,
            start_time=start,
            end_time=end,
            status=TaskStatus.SCHEDULED,
            scheduling_reason=None,
            scheduling_detail=None,
        )
        self._session.commit()
        return updated or ctx.task

    def local_reschedule(
        self, user_id: int, plan_id: int, task_id: int
    ) -> list[Task]:
        ctx = self._load(user_id, plan_id, task_id)
        start_task = ctx.task
        if start_task.occurrence_date is not None:
            raise DomainValidationError(
                "重复任务不能使用「从这里顺延」",
                detail={"reason_code": "RECURRING_NOT_RESCHEDULABLE"},
            )
        if start_task.status in _NON_MOVABLE_STATUSES:
            raise ConflictError("当前任务状态不允许重新安排")
        if start_task.status not in _MOVABLE_STATUSES:
            raise ConflictError("当前任务状态不允许重新安排")

        sequence = self._select_sequence(ctx, start_task)
        eligible = [
            item
            for item in sequence
            if item.status not in _NON_MOVABLE_STATUSES and item.id is not None
        ]
        if not eligible:
            raise ConflictError("没有可顺延的未完成任务")
        eligible_ids = {item.id for item in eligible}
        occupied = self._occupied_schedule(ctx, exclude_ids=eligible_ids)

        schedule = self._scheduler.schedule_sequence(
            eligible, ctx.rule_context, occupied=occupied
        )
        if schedule.unscheduled_task_ids:
            details = [
                {
                    "task_id": task_id_,
                    "code": schedule.unscheduled_reasons[task_id_].code,
                    "message": schedule.unscheduled_reasons[task_id_].message,
                }
                for task_id_ in schedule.unscheduled_task_ids
                if task_id_ in schedule.unscheduled_reasons
            ]
            raise DomainValidationError(
                "按当前剩余时间和约束，无法仅通过顺延完成后续任务。",
                detail={
                    "reason_code": "LOCAL_RESCHEDULE_INFEASIBLE",
                    "unscheduled": details,
                },
            )

        violations = self._sequence_violations(ctx, schedule, eligible_ids)
        if violations:
            first = violations[0]
            raise DomainValidationError(
                f"顺延后的安排不合法：{_reason_text(first)}",
                detail={
                    "reason_code": "LOCAL_RESCHEDULE_INFEASIBLE",
                    "rule": first.rule,
                    "violation_code": first.code,
                    "message": first.message,
                },
            )

        updated: list[Task] = []
        for placed in schedule.tasks:
            item = self._tasks.update_fields(
                placed.task_id,
                scheduled_date=placed.scheduled_date,
                start_time=placed.start_time,
                end_time=placed.end_time,
                status=TaskStatus.SCHEDULED,
                scheduling_reason=None,
                scheduling_detail=None,
            )
            if item is not None:
                updated.append(item)
        self._session.commit()
        return updated

    # ------------------------------------------------------------------
    # Shared validation (also used by PlanService.update_task)
    # ------------------------------------------------------------------
    def validate_placement(
        self,
        user_id: int,
        plan_id: int,
        task_id: int,
        *,
        target_date: date,
        start: time,
        end: time | None = None,
        enforce_now: bool = False,
    ) -> tuple[time, time]:
        """Validate a precise placement for an existing task.

        Returns the normalized ``(start, end)``. Raises
        :class:`DomainValidationError` with a deterministic reason code.
        """
        ctx = self._load(user_id, plan_id, task_id, extra_end=target_date)
        self._assert_movable(ctx.task)
        duration = _duration(ctx.task)
        if end is None:
            end = add_minutes(start, duration)
        self._validate_target_day(ctx, target_date, start, enforce_now=enforce_now)
        self._validate_placement(ctx, ctx.task, target_date, start, end, duration)
        return start, end

    def _validate_placement(
        self,
        ctx: _PlacementContext,
        task: Task,
        target_date: date,
        start: time,
        end: time,
        duration: int,
    ) -> None:
        if time_to_minutes(end) <= time_to_minutes(start):
            raise DomainValidationError(
                "结束时间必须晚于开始时间",
                detail={"reason_code": "OUTSIDE_AVAILABLE_WINDOW"},
            )
        schedule = self._day_schedule(ctx, task, target_date, start, end, duration)
        violations = self._rules.hard_violations(schedule, ctx.rule_context)
        relevant = [
            item
            for item in violations
            if not item.task_ids or (task.id is not None and task.id in item.task_ids)
        ]
        if relevant:
            first = relevant[0]
            raise DomainValidationError(
                _reason_text(first),
                detail={
                    "reason_code": first.code or first.rule,
                    "rule": first.rule,
                    "message": first.message,
                },
            )

    def _validate_target_day(
        self,
        ctx: _PlacementContext,
        target_date: date,
        start: time,
        *,
        enforce_now: bool,
    ) -> None:
        if target_date < ctx.today:
            raise DomainValidationError(
                "不能安排到过去的日期",
                detail={"reason_code": "PAST_DATE"},
            )
        if enforce_now and target_date == ctx.today and start < ctx.now_time:
            raise DomainValidationError(
                "不能安排到今天已经过去的时间",
                detail={"reason_code": "PAST_TIME"},
            )
        if ctx.task.occurrence_date is not None and (
            target_date != ctx.task.occurrence_date
        ):
            raise DomainValidationError(
                "重复任务只能调整当天时间，不能改到其他日期",
                detail={"reason_code": "RECURRING_WRONG_DAY"},
            )

    def _day_schedule(
        self,
        ctx: _PlacementContext,
        task: Task,
        target_date: date,
        start: time,
        end: time,
        duration: int,
    ) -> CandidateSchedule:
        members: list[ScheduledTask] = [self._as_scheduled(task, target_date, start, end, duration)]
        for other in ctx.tasks:
            if other.id == task.id or other.scheduled_date != target_date:
                continue
            if other.status == TaskStatus.SKIPPED:
                continue
            if other.start_time is None or other.end_time is None:
                continue
            other_duration = max(
                1, time_to_minutes(other.end_time) - time_to_minutes(other.start_time)
            )
            members.append(
                self._as_scheduled(
                    other,
                    target_date,
                    other.start_time,
                    other.end_time,
                    other_duration,
                )
            )
        return CandidateSchedule(
            start_date=target_date,
            end_date=target_date,
            tasks=members,
        )

    @staticmethod
    def _as_scheduled(
        task: Task, day: date, start: time, end: time, duration: int
    ) -> ScheduledTask:
        return ScheduledTask(
            task_id=task.id or 0,
            title=task.title,
            goal_id=task.goal_id,
            scheduled_date=day,
            start_time=start,
            end_time=end,
            duration_minutes=max(1, duration),
            cognitive_load=task.cognitive_load,
            priority=task.priority,
            completion_probability=(
                task.completion_probability
                if task.completion_probability is not None
                else 1.0
            ),
            is_flexible=task.is_flexible,
            series_id=task.series_id,
            occurrence_date=task.occurrence_date,
        )

    # ------------------------------------------------------------------
    # Loading and guards
    # ------------------------------------------------------------------
    def _load(
        self,
        user_id: int,
        plan_id: int,
        task_id: int,
        *,
        extra_end: date | None = None,
    ) -> _PlacementContext:
        plan = self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError("plan not found")
        if plan.user_id != user_id:
            raise PermissionDeniedError("plan belongs to another user")
        if plan.status != PlanStatus.ACTIVE:
            raise ConflictError("plan is not active")

        task = self._tasks.get_by_id(task_id)
        if task is None or task.plan_id != plan_id:
            raise NotFoundError("task not found in plan")

        tasks = self._tasks.list_by_plan(plan_id)
        goal_ids = {item.goal_id for item in tasks if item.goal_id is not None}
        goals = {
            goal.id: goal
            for goal in (self._goals.list_by_ids(sorted(goal_ids)) if goal_ids else [])
            if goal.id is not None
        }

        user = self._users.get_by_id(user_id)
        profile = dict(user.profile) if user is not None else {}
        stored = dict(user.scheduling_preferences) if user is not None else {}
        prefs = effective_scheduling_preferences(profile, stored)

        today = local_today()
        now = local_now()
        now_time = now.time().replace(tzinfo=None, microsecond=0)

        horizon_end = max(plan.end_date, today + timedelta(days=_HORIZON_DAYS))
        for item in tasks:
            if item.scheduled_date is not None:
                horizon_end = max(horizon_end, item.scheduled_date)
        for goal in goals.values():
            if goal.deadline is not None:
                horizon_end = max(horizon_end, goal.deadline.date())
        if extra_end is not None:
            horizon_end = max(horizon_end, extra_end)

        schedule_events = self._events.list_range(user_id, today, horizon_end)
        fixed_events = [
            FixedEvent(
                date=item.date,
                start_time=item.start_time,
                end_time=item.end_time,
                title=item.title,
            )
            for item in expand_fixed_events(schedule_events, today, horizon_end)
        ]

        task_deadlines: dict[int, date] = {}
        task_earliest: dict[int, date] = {}
        for item in tasks:
            if item.id is None:
                continue
            goal = goals.get(item.goal_id) if item.goal_id is not None else None
            if goal is None:
                continue
            deadline = goal.deadline.date() if goal.deadline is not None else None
            if deadline is not None:
                task_deadlines[item.id] = deadline
            try:
                earliest = resolve_earliest_start(
                    goal.start_date,
                    text=" ".join(filter(None, [goal.title, goal.description])),
                    deadline=deadline,
                    reference=plan.start_date,
                )
            except Exception:  # noqa: BLE001 - invalid goal window is a validation problem
                earliest = goal.start_date
            if earliest is not None:
                task_earliest[item.id] = earliest

        completed = {
            item.id
            for item in tasks
            if item.id is not None and item.status == TaskStatus.COMPLETED
        }
        preferred_slots = dict(profile.get("preferred_time_slots") or {})
        raw_conflicts = profile.get("conflicting_subject_pairs") or [("math", "algorithm")]
        conflicts = [tuple(pair) for pair in raw_conflicts if isinstance(pair, (list, tuple))]

        rule_context = RuleContext(
            daily_limit_minutes=prefs["daily_limit_minutes"],
            buffer_minutes=prefs["buffer_minutes"],
            high_cognitive_max_per_day=prefs["high_cognitive_max_per_day"],
            max_daily_minutes_per_goal=prefs["max_daily_minutes_per_goal"],
            available_minutes_per_day=prefs["available_minutes_per_day"],
            day_start=_parse_time(profile.get("day_start"), DEFAULT_DAY_START),
            day_end=_parse_time(profile.get("day_end"), DEFAULT_DAY_END),
            not_before={today: now_time},
            today=today,
            preferred_time_slots=preferred_slots,
            schedule_start=today,
            schedule_end=horizon_end,
            task_deadlines=task_deadlines,
            task_earliest_dates=task_earliest,
            completed_task_ids=completed,
            conflicting_subject_pairs=conflicts,
            fixed_events=fixed_events,
        )
        return _PlacementContext(
            plan=plan,
            task=task,
            tasks=tasks,
            goals=goals,
            rule_context=rule_context,
            today=today,
            now_time=now_time,
        )

    def _assert_backloggable(self, ctx: _PlacementContext) -> None:
        task = ctx.task
        if task.status not in _BACKLOG_STATUSES:
            raise ConflictError("当前任务状态不允许放入任务池")
        if task.occurrence_date is not None:
            raise DomainValidationError(
                "重复任务不能放入任务池",
                detail={"reason_code": "RECURRING_NOT_BACKLOGGABLE"},
            )

    def _assert_movable(self, task: Task) -> None:
        if task.status not in _MOVABLE_STATUSES:
            raise ConflictError("当前任务状态不允许移动")
        if task.deleted_at is not None:
            raise NotFoundError("task not found in plan")

    # ------------------------------------------------------------------
    # Sequence helpers
    # ------------------------------------------------------------------
    def _select_sequence(self, ctx: _PlacementContext, start: Task) -> list[Task]:
        """Tasks from ``start`` onward in the same project series.

        ``series_id`` + ``goal_id`` define the project scope; ``order_index`` is
        the deterministic materialization order inside one plan version. Plain
        one-off tasks (no series) form a single-task sequence.
        """
        if start.series_id is None:
            return [start]
        candidates = [
            item
            for item in ctx.tasks
            if item.goal_id == start.goal_id
            and item.series_id == start.series_id
            and item.occurrence_date is None
            and item.order_index >= start.order_index
        ]
        return sorted(candidates, key=lambda item: (item.order_index, item.id or 0))

    def _occupied_schedule(
        self, ctx: _PlacementContext, *, exclude_ids: set[int | None]
    ) -> CandidateSchedule:
        members: list[ScheduledTask] = []
        for item in ctx.tasks:
            if item.id in exclude_ids:
                continue
            if item.status in {TaskStatus.SKIPPED, TaskStatus.MISSED}:
                continue
            if (
                item.scheduled_date is None
                or item.start_time is None
                or item.end_time is None
            ):
                continue
            duration = max(
                1, time_to_minutes(item.end_time) - time_to_minutes(item.start_time)
            )
            members.append(
                self._as_scheduled(
                    item,
                    item.scheduled_date,
                    item.start_time,
                    item.end_time,
                    duration,
                )
            )
        return CandidateSchedule(
            start_date=ctx.today,
            end_date=ctx.rule_context.schedule_end or ctx.today,
            tasks=members,
        )

    def _sequence_violations(
        self,
        ctx: _PlacementContext,
        schedule: CandidateSchedule,
        eligible_ids: set[int],
    ) -> list[RuleViolation]:
        violations = self._rules.hard_violations(schedule, ctx.rule_context)
        return [
            item
            for item in violations
            if not item.task_ids or any(task_id in eligible_ids for task_id in item.task_ids)
        ]


__all__ = ["TaskSchedulingService"]
