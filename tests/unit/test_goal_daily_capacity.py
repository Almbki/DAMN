"""HARD per-goal daily minutes cap (default 120)."""

from __future__ import annotations

from datetime import date, time, timedelta

from app.domain.models import Task
from app.domain.models.enums import CognitiveLoad, Priority, TaskKind
from app.domain.rules.base import RuleContext
from app.domain.rules.goal_daily_capacity import GoalDailyCapacityRule
from app.domain.scheduling.constants import GOAL_DAILY_CAPACITY_EXCEEDED
from app.domain.scheduling.schedule_result import CandidateSchedule, ScheduledTask
from app.domain.scheduling.scheduler import Scheduler

START = date(2026, 11, 1)


def _context(*, end: date | None = None, cap: int = 120) -> RuleContext:
    return RuleContext(
        daily_limit_minutes=300,
        available_minutes_per_day=480,
        buffer_minutes=15,
        high_cognitive_max_per_day=2,
        max_daily_minutes_per_goal=cap,
        day_start=time(8, 0),
        day_end=time(22, 0),
        today=START,
        schedule_start=START,
        schedule_end=end or (START + timedelta(days=4)),
    )


def _task(
    task_id: int,
    minutes: int,
    goal_id: int | None,
    *,
    occurrence: date | None = None,
    series_id: str | None = None,
) -> Task:
    return Task(
        id=task_id,
        plan_id=0,
        title=f"task-{task_id}",
        goal_id=goal_id,
        estimated_duration=minutes,
        cognitive_load=CognitiveLoad.MEDIUM,
        priority=Priority.MEDIUM,
        task_kind=TaskKind.ROUTINE if occurrence else TaskKind.ONE_OFF,
        series_id=series_id,
        occurrence_date=occurrence,
        order_index=task_id - 1,
    )


def _goal_day_totals(schedule: CandidateSchedule) -> dict[tuple[int, date], int]:
    totals: dict[tuple[int, date], int] = {}
    for task in schedule.tasks:
        if task.goal_id is None:
            continue
        key = (task.goal_id, task.scheduled_date)
        totals[key] = totals.get(key, 0) + task.duration_minutes
    return totals


def test_four_75_minute_chunks_do_not_all_fit_on_one_day() -> None:
    tasks = [_task(i, 75, 1) for i in range(1, 5)]
    schedule = Scheduler().schedule(tasks, _context())

    assert len(schedule.tasks) == 4
    totals = _goal_day_totals(schedule)
    assert max(totals.values()) <= 120
    assert len({task.scheduled_date for task in schedule.tasks}) == 4


def test_multiple_work_units_share_one_goal_budget() -> None:
    tasks = [_task(1, 60, 1), _task(2, 60, 1), _task(3, 30, 1)]
    schedule = Scheduler().schedule(tasks, _context(end=START + timedelta(days=1)))

    assert len(schedule.tasks) == 3
    totals = _goal_day_totals(schedule)
    assert totals[(1, START)] == 120
    assert totals[(1, START + timedelta(days=1))] == 30


def test_only_remaining_60_minutes_are_available() -> None:
    tasks = [_task(1, 60, 1), _task(2, 75, 1)]
    schedule = Scheduler().schedule(tasks, _context(end=START + timedelta(days=1)))

    assert len(schedule.tasks) == 2
    by_id = {task.task_id: task for task in schedule.tasks}
    assert by_id[1].scheduled_date == START
    assert by_id[2].scheduled_date == START + timedelta(days=1)


def test_recurring_occurrence_counts_toward_goal_budget() -> None:
    occurrence = _task(1, 60, 1, occurrence=START, series_id="english")
    one_off = _task(2, 75, 1)
    context = _context(end=START + timedelta(days=1))
    context.task_deadlines = {1: START}
    context.task_earliest_dates = {1: START}

    schedule = Scheduler().schedule([occurrence, one_off], context)
    by_id = {task.task_id: task for task in schedule.tasks}

    assert by_id[1].scheduled_date == START
    assert by_id[2].scheduled_date == START + timedelta(days=1)
    totals = _goal_day_totals(schedule)
    assert totals[(1, START)] == 60
    assert totals[(1, START + timedelta(days=1))] == 75


def test_different_goals_have_independent_budgets() -> None:
    tasks = [_task(1, 100, 1), _task(2, 100, 2)]
    schedule = Scheduler().schedule(tasks, _context(end=START))

    assert len(schedule.tasks) == 2
    totals = _goal_day_totals(schedule)
    assert totals[(1, START)] == 100
    assert totals[(2, START)] == 100


def test_goal_over_cap_returns_specific_pending_reason() -> None:
    schedule = Scheduler().schedule([_task(1, 130, 1)], _context(end=START))

    assert schedule.unscheduled_task_ids == [1]
    failure = schedule.unscheduled_reasons[1]
    assert failure.code == GOAL_DAILY_CAPACITY_EXCEEDED
    assert failure.needed_minutes == 130


def test_rule_flags_goal_over_cap() -> None:
    schedule = CandidateSchedule(
        start_date=START,
        end_date=START,
        tasks=[
            _placed(1, time(9, 0), 75, 1),
            _placed(2, time(10, 30), 75, 1),
        ],
    )
    violations = GoalDailyCapacityRule().validate(
        schedule, RuleContext(max_daily_minutes_per_goal=120)
    )
    assert [violation.code for violation in violations] == [
        GOAL_DAILY_CAPACITY_EXCEEDED
    ]


def test_rule_allows_exact_goal_cap() -> None:
    schedule = CandidateSchedule(
        start_date=START,
        end_date=START,
        tasks=[
            _placed(1, time(9, 0), 60, 1),
            _placed(2, time(10, 15), 60, 1),
        ],
    )
    assert (
        GoalDailyCapacityRule().validate(
            schedule, RuleContext(max_daily_minutes_per_goal=120)
        )
        == []
    )


def test_default_goal_daily_cap_is_120() -> None:
    assert RuleContext().max_daily_minutes_per_goal == 120


def _placed(task_id: int, start: time, minutes: int, goal_id: int) -> ScheduledTask:
    start_minutes = start.hour * 60 + start.minute
    end_minutes = start_minutes + minutes
    return ScheduledTask(
        task_id=task_id,
        title=f"task-{task_id}",
        goal_id=goal_id,
        scheduled_date=START,
        start_time=start,
        end_time=time(end_minutes // 60, end_minutes % 60),
        duration_minutes=minutes,
        cognitive_load=CognitiveLoad.MEDIUM,
        priority=Priority.MEDIUM,
    )
