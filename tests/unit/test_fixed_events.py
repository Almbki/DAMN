"""Scheduler / rule-engine behaviour around imported fixed events."""

from __future__ import annotations

from datetime import date, time

from app.domain.models import Task
from app.domain.models.enums import Priority, TaskStatus
from app.domain.models.schedule_event import ScheduleEvent
from app.domain.rules.base import RuleContext, RuleEngine
from app.domain.scheduling.fixed_events import events_overlap, expand_fixed_events
from app.domain.scheduling.schedule_result import (
    CandidateSchedule,
    FixedEvent,
    ScheduledTask,
)
from app.domain.scheduling.scheduler import Scheduler


def _task(minutes: int = 60) -> Task:
    return Task(
        id=1,
        plan_id=1,
        title="Study",
        estimated_duration=minutes,
        priority=Priority.HIGH,
        status=TaskStatus.SCHEDULED,
        order_index=1,
    )


def _context(**overrides) -> RuleContext:
    base = dict(
        daily_limit_minutes=300,
        buffer_minutes=15,
        high_cognitive_max_per_day=2,
        available_minutes_per_day=480,
        day_start=time(8, 0),
        day_end=time(22, 0),
    )
    base.update(overrides)
    return RuleContext(**base)


def test_scheduler_avoids_fixed_event() -> None:
    today = date.today()
    context = _context(
        day_start=time(9, 0),
        day_end=time(22, 0),
        fixed_events=[
            FixedEvent(
                date=today,
                start_time=time(9, 0),
                end_time=time(11, 0),
                title="Math lecture",
            )
        ],
    )
    schedule = Scheduler().schedule([_task(60)], context)

    assert len(schedule.tasks) == 1
    placed = schedule.tasks[0]
    assert placed.scheduled_date == today
    assert placed.start_time >= time(11, 0)
    assert RuleEngine().hard_violations(schedule, context) == []


def test_rule_reports_fixed_event_overlap_when_task_is_forced() -> None:
    day = date(2026, 11, 2)
    schedule = CandidateSchedule(
        start_date=day,
        end_date=day,
        tasks=[
            ScheduledTask(
                task_id=1,
                title="Study",
                scheduled_date=day,
                start_time=time(9, 30),
                end_time=time(10, 30),
                duration_minutes=60,
            )
        ],
    )
    context = _context(
        fixed_events=[
            FixedEvent(
                date=day,
                start_time=time(9, 0),
                end_time=time(11, 0),
                title="Math lecture",
            )
        ]
    )
    violations = RuleEngine().hard_violations(schedule, context)
    assert any(v.code == "fixed_event_overlap" for v in violations)
    assert any(v.task_ids == [1] for v in violations)


def test_no_fixed_events_keeps_previous_behaviour() -> None:
    schedule = Scheduler().schedule([_task(60)], _context())
    assert len(schedule.tasks) == 1
    assert RuleEngine().hard_violations(schedule, _context()) == []


def test_expand_weekly_recurrence() -> None:
    event = ScheduleEvent(
        user_id=1,
        title="Algorithms",
        weekdays=[0],  # Monday
        start_time=time(10, 0),
        end_time=time(12, 0),
    )
    expanded = expand_fixed_events(
        [event], date(2026, 11, 2), date(2026, 11, 15)
    )
    assert [item.date for item in expanded] == [
        date(2026, 11, 2),
        date(2026, 11, 9),
    ]
    assert all(item.title == "Algorithms" for item in expanded)


def test_recurring_event_does_not_conflict_with_other_weekday() -> None:
    weekly = ScheduleEvent(
        user_id=1,
        title="Monday lecture",
        weekdays=[0],
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    tuesday = ScheduleEvent(
        user_id=1,
        title="Tuesday exam",
        start_date=date(2026, 11, 3),  # Tuesday
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    monday = ScheduleEvent(
        user_id=1,
        title="Monday exam",
        start_date=date(2026, 11, 2),  # Monday
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    assert events_overlap(weekly, tuesday) is False
    assert events_overlap(weekly, monday) is True


def test_expand_event_respects_date_bounds() -> None:
    event = ScheduleEvent(
        user_id=1,
        title="Exam week",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 4),
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    expanded = expand_fixed_events(
        [event], date(2026, 11, 1), date(2026, 11, 10)
    )
    assert [item.date for item in expanded] == [
        date(2026, 11, 2),
        date(2026, 11, 3),
        date(2026, 11, 4),
    ]
    assert all(
        (item.end_time.hour * 60 + item.end_time.minute)
        - (item.start_time.hour * 60 + item.start_time.minute)
        == 60
        for item in expanded
    )
