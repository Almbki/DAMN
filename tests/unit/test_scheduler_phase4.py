"""Phase 4 scheduler: daily capacity, packing order, reasons, daily plans.

Coverage for the daily-arrangement workflow:
* capacity = min(daily limit, available - fixed events), burst reserve kept free;
* packing order pinned -> long-term wait/floor -> deadline -> chores -> rest;
* unscheduled reasons instead of silent drops;
* DailyPlan reporting;
* the two new repositories writing/reading their rows.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, time, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.domain.models import Task
from app.domain.models.daily_plan import DailyPlanRecord
from app.domain.models.enums import CognitiveLoad, Priority, TaskKind, TaskStatus
from app.domain.models.unscheduled_task import UnscheduledTaskRecord
from app.domain.rules.base import RuleContext, RuleEngine
from app.domain.scheduling.daily_plan import (
    REASON_CAPACITY,
    REASON_DEADLINE,
    REASON_LONG_TERM_WAIT,
    REASON_NO_SLOT,
)
from app.domain.scheduling.schedule_result import CandidateSchedule, FixedEvent
from app.domain.scheduling.scheduler import Scheduler, SchedulerConfig
from app.infrastructure.database import Base
from app.infrastructure.database.models import daily_plan as _daily_plan_orm  # noqa: F401
from app.infrastructure.database.models import unscheduled_task as _unscheduled_orm  # noqa: F401
from app.infrastructure.database.repositories.daily_plan_repository import (
    DailyPlanRepository,
)
from app.infrastructure.database.repositories.unscheduled_task_repository import (
    UnscheduledTaskRepository,
)

TODAY = date(2026, 3, 2)
TOMORROW = TODAY + timedelta(days=1)


def _context(**overrides: object) -> RuleContext:
    data: dict[str, object] = {
        "daily_limit_minutes": 480,
        "buffer_minutes": 15,
        "high_cognitive_max_per_day": 2,
        "available_minutes_per_day": 480,
        "day_start": time(8, 0),
        "day_end": time(22, 0),
        "today": TODAY,
    }
    data.update(overrides)
    return RuleContext(**data)  # type: ignore[arg-type]


def _task(task_id: int, minutes: int, **overrides: object) -> Task:
    data: dict[str, object] = {
        "id": task_id,
        "plan_id": 1,
        "title": f"T{task_id}",
        "estimated_duration": minutes,
        "cognitive_load": CognitiveLoad.MEDIUM,
        "priority": Priority.MEDIUM,
        "status": TaskStatus.SCHEDULED,
        "order_index": task_id,
    }
    data.update(overrides)
    return Task(**data)  # type: ignore[arg-type]


def _scheduler(**overrides: object) -> Scheduler:
    config: dict[str, object] = {
        "burst_reserve_minutes": 10,
        "long_term_daily_floor_minutes": 30,
        "deadline_acceleration_days": 3,
        "long_term_max_wait_days": 7,
    }
    config.update(overrides)
    return Scheduler(SchedulerConfig(**config))  # type: ignore[arg-type]


def _plan_on(schedule: CandidateSchedule, day: date):
    return next(plan for plan in schedule.daily_plans if plan.date == day)


# ---------------------------------------------------------------------------
# Capacity and reserve
# ---------------------------------------------------------------------------
def test_daily_capacity_subtracts_fixed_events() -> None:
    context = _context(
        available_minutes_per_day=300,
        daily_limit_minutes=480,
        fixed_events=[
            FixedEvent(
                date=TODAY,
                start_time=time(9, 0),
                end_time=time(11, 0),
                title="Lecture",
            )
        ],
    )
    schedule = _scheduler(burst_reserve_minutes=10).schedule([_task(1, 60)], context)

    assert len(schedule.tasks) == 1
    today = _plan_on(schedule, TODAY)
    # min(daily_limit=480, available - fixed = 300 - 120) == 180.
    assert today.capacity_minutes == 180
    assert today.used_minutes == 60
    assert today.task_ids == [1]
    assert "fixed_events=120" in today.reasons
    assert "burst_reserve=10" in today.reasons
    assert len(schedule.daily_plans) == 14  # inclusive default horizon
    assert schedule.unscheduled_reasons == {}
    assert RuleEngine().hard_violations(schedule, context) == []


def test_daily_limit_remains_the_hard_upper_bound() -> None:
    context = _context(available_minutes_per_day=480, daily_limit_minutes=90)
    schedule = _scheduler(burst_reserve_minutes=0).schedule(
        [_task(1, 60), _task(2, 60)], context
    )

    assert all(minutes <= 90 for minutes in schedule.daily_minutes().values())
    assert _plan_on(schedule, TODAY).capacity_minutes == 90


def test_burst_reserve_keeps_capacity_free() -> None:
    context = _context(
        available_minutes_per_day=480,
        daily_limit_minutes=180,
        task_deadlines={1: TODAY, 2: TODAY, 3: TODAY},
    )
    tasks = [_task(task_id, 60) for task_id in (1, 2, 3)]

    schedule = _scheduler(burst_reserve_minutes=60).schedule(tasks, context)

    today = _plan_on(schedule, TODAY)
    assert today.capacity_minutes == 180
    assert today.used_minutes == 120  # the 60-minute burst reserve is untouched
    assert schedule.unscheduled_task_ids == [3]


# ---------------------------------------------------------------------------
# Packing order
# ---------------------------------------------------------------------------
def test_pinned_tasks_are_packed_before_flexible_work() -> None:
    context = _context(
        daily_limit_minutes=60,
        task_deadlines={1: TODAY, 2: TODAY},
    )
    pinned = _task(1, 60, is_flexible=False, priority=Priority.LOW)
    urgent = _task(2, 60, priority=Priority.CRITICAL)

    schedule = _scheduler(burst_reserve_minutes=0).schedule([urgent, pinned], context)

    assert [task.task_id for task in schedule.tasks] == [1]
    assert schedule.unscheduled_task_ids == [2]
    assert schedule.unscheduled_reasons[2] == REASON_DEADLINE


def test_long_term_floor_is_protected_from_other_work() -> None:
    context = _context(
        daily_limit_minutes=180,
        task_earliest_dates={1: TOMORROW},
        task_deadlines={2: TODAY},
    )
    long_term = _task(1, 60, task_kind=TaskKind.LONG_TERM)
    deadline_task = _task(2, 150, priority=Priority.HIGH)

    schedule = _scheduler(
        burst_reserve_minutes=0, long_term_daily_floor_minutes=60
    ).schedule([deadline_task, long_term], context)

    placed = {task.task_id: task.scheduled_date for task in schedule.tasks}
    assert placed == {1: TOMORROW}
    # 150 <= 180 raw minutes, but 60 are protected for long-term work.
    assert schedule.unscheduled_reasons[2] == REASON_CAPACITY


def test_waiting_long_term_task_moves_to_the_front() -> None:
    context = _context(
        daily_limit_minutes=60,
        task_earliest_dates={1: TODAY - timedelta(days=8)},
        task_deadlines={1: TODAY, 2: TODAY},
    )
    waiting = _task(1, 60, task_kind=TaskKind.LONG_TERM)
    fresh = _task(2, 60, task_kind=TaskKind.LONG_TERM, order_index=0)

    schedule = _scheduler(burst_reserve_minutes=0).schedule([fresh, waiting], context)

    assert [task.task_id for task in schedule.tasks] == [1]
    assert schedule.unscheduled_reasons[2] == REASON_DEADLINE


def test_deadline_tasks_accelerate_ahead_of_general_work() -> None:
    context = _context(daily_limit_minutes=60, task_deadlines={1: TODAY})
    deadline_task = _task(1, 60, priority=Priority.LOW)
    general = _task(2, 60, priority=Priority.CRITICAL)

    schedule = _scheduler(burst_reserve_minutes=0).schedule(
        [general, deadline_task], context
    )

    placed = {task.task_id: task.scheduled_date for task in schedule.tasks}
    assert placed[1] == TODAY
    assert placed[2] == TOMORROW


def test_low_priority_chores_are_packed_before_general_work() -> None:
    context = _context(daily_limit_minutes=60)
    chore = _task(1, 60, priority=Priority.LOW)
    general = _task(2, 60, priority=Priority.CRITICAL)

    schedule = _scheduler(burst_reserve_minutes=0).schedule([general, chore], context)

    placed = {task.task_id: task.scheduled_date for task in schedule.tasks}
    assert placed[1] == TODAY
    assert placed[2] == TOMORROW


# ---------------------------------------------------------------------------
# Unscheduled reasons
# ---------------------------------------------------------------------------
def test_unscheduled_capacity_reason_is_recorded() -> None:
    context = _context(daily_limit_minutes=60)
    schedule = _scheduler(burst_reserve_minutes=0).schedule([_task(1, 120)], context)

    assert schedule.unscheduled_task_ids == [1]
    assert schedule.unscheduled_reasons[1] == REASON_CAPACITY
    assert schedule.unscheduled_tasks[0].task_id == 1
    assert schedule.unscheduled_tasks[0].reason == REASON_CAPACITY


def test_unscheduled_deadline_reason_is_recorded() -> None:
    context = _context(
        daily_limit_minutes=60,
        task_deadlines={1: TODAY, 2: TODAY},
    )
    first = _task(1, 60, is_flexible=False)
    second = _task(2, 60)

    schedule = _scheduler(burst_reserve_minutes=0).schedule([first, second], context)

    assert schedule.unscheduled_task_ids == [2]
    assert schedule.unscheduled_reasons[2] == REASON_DEADLINE
    assert schedule.unscheduled_tasks[0].date == TODAY


def test_long_term_wait_reason_is_recorded() -> None:
    context = _context(
        day_start=time(9, 0),
        day_end=time(10, 0),
        task_earliest_dates={1: TODAY - timedelta(days=8)},
    )
    task = _task(1, 90, task_kind=TaskKind.LONG_TERM)

    schedule = _scheduler(burst_reserve_minutes=0).schedule([task], context)

    assert schedule.unscheduled_reasons[1] == REASON_LONG_TERM_WAIT


def test_no_slot_reason_is_recorded() -> None:
    context = _context(day_start=time(9, 0), day_end=time(10, 0))
    schedule = _scheduler(burst_reserve_minutes=0).schedule([_task(1, 90)], context)

    assert schedule.unscheduled_reasons[1] == REASON_NO_SLOT


# ---------------------------------------------------------------------------
# DailyPlan output / backward compatibility
# ---------------------------------------------------------------------------
def test_daily_plans_report_capacity_usage_and_tasks() -> None:
    context = _context(daily_limit_minutes=120)
    tasks = [
        _task(1, 60, cognitive_load=CognitiveLoad.HIGH),
        _task(2, 30),
    ]

    schedule = _scheduler(burst_reserve_minutes=0).schedule(tasks, context)

    today = _plan_on(schedule, TODAY)
    assert today.capacity_minutes == 120
    assert today.used_minutes == 90
    assert today.task_ids == [1, 2]
    assert "daily_limit=120" in today.reasons
    assert schedule.unscheduled_reasons == {}
    assert RuleEngine().hard_violations(schedule, context) == []


def test_candidate_schedule_new_fields_default_to_empty() -> None:
    schedule = CandidateSchedule(start_date=TODAY, end_date=TODAY)

    assert schedule.daily_plans == []
    assert schedule.unscheduled_reasons == {}
    assert schedule.unscheduled_tasks == []


def test_scheduler_config_reads_settings_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Settings:
        burst_reserve_minutes = 0
        long_term_daily_floor_minutes = 5
        deadline_acceleration_days = 1
        long_term_max_wait_days = 2

    monkeypatch.setattr("app.core.config.get_settings", lambda: _Settings())

    config = SchedulerConfig.from_settings()

    assert config.burst_reserve_minutes == 0
    assert config.long_term_daily_floor_minutes == 5
    assert config.deadline_acceleration_days == 1
    assert config.long_term_max_wait_days == 2


# ---------------------------------------------------------------------------
# Persistence: daily_plans / unscheduled_tasks
# ---------------------------------------------------------------------------
@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def test_daily_plan_repository_roundtrip(session: Session) -> None:
    repository = DailyPlanRepository(session)
    created = repository.create_many(
        [
            DailyPlanRecord(
                plan_id=7,
                date=TODAY,
                capacity_minutes=240,
                used_minutes=60,
                tasks=[1],
                reasons=["daily_limit=300", "burst_reserve=60"],
            )
        ]
    )

    assert created[0].id is not None
    rows = repository.list_by_plan(7)
    assert len(rows) == 1
    assert rows[0].date == TODAY
    assert rows[0].capacity_minutes == 240
    assert rows[0].used_minutes == 60
    assert rows[0].tasks == [1]
    assert rows[0].reasons == ["daily_limit=300", "burst_reserve=60"]
    assert repository.delete_by_plan(7) == 1
    assert repository.list_by_plan(7) == []


def test_unscheduled_task_repository_roundtrip(session: Session) -> None:
    repository = UnscheduledTaskRepository(session)
    created = repository.create_many(
        [
            UnscheduledTaskRecord(
                plan_id=7,
                task_id=3,
                date=TODAY,
                reason=REASON_CAPACITY,
            )
        ]
    )

    assert created[0].id is not None
    rows = repository.list_by_plan(7)
    assert len(rows) == 1
    assert rows[0].task_id == 3
    assert rows[0].date == TODAY
    assert rows[0].reason == REASON_CAPACITY
    assert repository.delete_by_plan(7) == 1
    assert repository.list_by_plan(7) == []
