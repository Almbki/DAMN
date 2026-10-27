"""Scheduler diagnostics and scheduler-aware chunk sizes."""

from __future__ import annotations

from datetime import date, time

from app.domain.models import Task
from app.domain.rules.base import RuleContext
from app.domain.scheduling.schedule_result import FixedEvent
from app.domain.scheduling.scheduler import Scheduler


def test_unschedulable_task_has_structured_reason() -> None:
    task = Task(id=1, plan_id=0, title="big", estimated_duration=240)
    context = RuleContext(
        daily_limit_minutes=120,
        available_minutes_per_day=120,
        day_start=time(8, 0),
        day_end=time(22, 0),
    )

    schedule = Scheduler().schedule([task], context)

    assert schedule.unscheduled_task_ids == [1]
    reason = schedule.unscheduled_reasons[1]
    assert reason.code in {
        "DAILY_CAPACITY_EXCEEDED",
        "CONTIGUOUS_SLOT_TOO_SHORT",
    }
    assert reason.needed_minutes == 240


def test_max_contiguous_minutes_accounts_for_fixed_events() -> None:
    today = date.today()
    task = Task(id=1, plan_id=0, title="task", estimated_duration=60)
    context = RuleContext(
        day_start=time(8, 0),
        day_end=time(12, 0),
        fixed_events=[
            FixedEvent(
                date=today,
                start_time=time(8, 0),
                end_time=time(10, 0),
            )
        ],
        schedule_start=today,
        schedule_end=today,
    )

    assert Scheduler().max_contiguous_minutes(task, context) == 120
