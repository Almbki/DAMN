"""Unit tests for the heuristic scheduler."""

from __future__ import annotations

from datetime import date, time, timedelta

from app.domain.models import Task
from app.domain.models.enums import CognitiveLoad, Priority, TaskStatus
from app.domain.rules.base import RuleContext, RuleEngine
from app.domain.scheduling.scheduler import Scheduler


def _task(
    task_id: int,
    title: str,
    minutes: int,
    *,
    load: CognitiveLoad = CognitiveLoad.MEDIUM,
    priority: Priority = Priority.MEDIUM,
) -> Task:
    return Task(
        id=task_id,
        plan_id=1,
        title=title,
        estimated_duration=minutes,
        cognitive_load=load,
        priority=priority,
        status=TaskStatus.SCHEDULED,
        order_index=task_id,
    )


def _context(**overrides) -> RuleContext:
    base = dict(
        daily_limit_minutes=300,
        buffer_minutes=15,
        high_cognitive_max_per_day=1,
        available_minutes_per_day=480,
        day_start=time(8, 0),
        day_end=time(22, 0),
    )
    base.update(overrides)
    return RuleContext(**base)


def test_scheduler_places_all_tasks() -> None:
    tasks = [_task(1, "A", 60), _task(2, "B", 60)]
    schedule = Scheduler().schedule(tasks, _context())
    assert len(schedule.tasks) == 2
    assert schedule.unscheduled_task_ids == []


def test_scheduler_respects_daily_limit() -> None:
    context = _context(daily_limit_minutes=60)
    tasks = [_task(1, "A", 60), _task(2, "B", 60)]
    schedule = Scheduler().schedule(tasks, context)
    totals = schedule.daily_minutes()
    assert all(minutes <= 60 for minutes in totals.values())


def test_scheduler_skips_completed_tasks() -> None:
    tasks = [_task(1, "A", 60)]
    context = _context(completed_task_ids={1})
    schedule = Scheduler().schedule(tasks, context)
    assert schedule.tasks == []


def test_scheduler_splits_conflicting_subjects_across_days() -> None:
    tasks = [_task(1, "Math", 60), _task(2, "Algo", 60)]
    days = (date.today(), date.today() + timedelta(days=13))
    context = _context(task_subjects={1: "math", 2: "algorithm"})
    schedule = Scheduler().schedule(tasks, context)
    assert schedule.start_date == days[0]
    placed_days = {t.task_id: t.scheduled_date for t in schedule.tasks}
    assert placed_days[1] != placed_days[2]


def test_scheduler_output_validates_against_rules() -> None:
    tasks = [_task(1, "Math", 60, load=CognitiveLoad.HIGH), _task(2, "Rest", 30)]
    context = _context()
    schedule = Scheduler().schedule(tasks, context)
    violations = RuleEngine().hard_violations(schedule, context)
    assert violations == []
