"""Unit tests for the hard-constraint rule engine."""

from __future__ import annotations

from datetime import date, time

from app.domain.models.enums import CognitiveLoad, Priority
from app.domain.rules.base import RuleContext, RuleEngine
from app.domain.scheduling.schedule_result import CandidateSchedule, ScheduledTask

DAY = date(2026, 1, 5)


def _placed(
    task_id: int,
    start: time,
    end: time,
    *,
    load: CognitiveLoad = CognitiveLoad.MEDIUM,
    day: date = DAY,
    priority: Priority = Priority.MEDIUM,
) -> ScheduledTask:
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    return ScheduledTask(
        task_id=task_id,
        title=f"task-{task_id}",
        scheduled_date=day,
        start_time=start,
        end_time=end,
        duration_minutes=end_minutes - start_minutes,
        cognitive_load=load,
        priority=priority,
    )


def _schedule(tasks: list[ScheduledTask]) -> CandidateSchedule:
    return CandidateSchedule(start_date=DAY, end_date=DAY, tasks=tasks)


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


def _codes(violations) -> set[str]:
    return {v.code for v in violations if v.code}


def test_high_cognitive_consecutive_is_flagged() -> None:
    tasks = [
        _placed(1, time(9, 0), time(10, 0), load=CognitiveLoad.HIGH),
        _placed(2, time(10, 5), time(11, 5), load=CognitiveLoad.HIGH),
    ]
    violations = RuleEngine().hard_violations(_schedule(tasks), _context())
    assert "high_cognitive_consecutive" in _codes(violations)


def test_high_cognitive_with_gap_is_ok() -> None:
    tasks = [
        _placed(1, time(9, 0), time(10, 0), load=CognitiveLoad.HIGH),
        _placed(2, time(10, 40), time(11, 40), load=CognitiveLoad.HIGH),
    ]
    violations = RuleEngine().hard_violations(_schedule(tasks), _context())
    assert "high_cognitive_consecutive" not in _codes(violations)


def test_same_day_conflict_math_algorithm() -> None:
    tasks = [_placed(1, time(9, 0), time(10, 0)), _placed(2, time(14, 0), time(15, 0))]
    context = _context(task_subjects={1: "math", 2: "algorithm"})
    violations = RuleEngine().hard_violations(_schedule(tasks), context)
    assert "same_day_conflict" in _codes(violations)


def test_daily_limit_violation() -> None:
    tasks = [_placed(1, time(9, 0), time(12, 0)), _placed(2, time(14, 0), time(17, 0))]
    violations = RuleEngine().hard_violations(_schedule(tasks), _context(daily_limit_minutes=300))
    assert "daily_limit" in _codes(violations)


def test_buffer_violation() -> None:
    tasks = [_placed(1, time(9, 0), time(10, 0)), _placed(2, time(10, 5), time(11, 0))]
    violations = RuleEngine().hard_violations(_schedule(tasks), _context(buffer_minutes=15))
    assert "insufficient_buffer" in _codes(violations)


def test_deadline_violation() -> None:
    tasks = [_placed(1, time(9, 0), time(10, 0))]
    context = _context(task_deadlines={1: date(2026, 1, 4)})
    violations = RuleEngine().hard_violations(_schedule(tasks), context)
    assert "deadline_exceeded" in _codes(violations)


def test_completed_task_rescheduled() -> None:
    tasks = [_placed(1, time(9, 0), time(10, 0))]
    context = _context(completed_task_ids={1})
    violations = RuleEngine().hard_violations(_schedule(tasks), context)
    assert "completed_task_rescheduled" in _codes(violations)


def test_outside_available_window() -> None:
    tasks = [_placed(1, time(7, 0), time(8, 0))]
    violations = RuleEngine().hard_violations(_schedule(tasks), _context())
    assert "outside_available_window" in _codes(violations)


def test_default_rules_has_seven_constraints() -> None:
    engine = RuleEngine()
    names = {rule.name for rule in engine.rules}
    assert {
        "high_cognitive_not_consecutive",
        "same_day_conflict",
        "daily_limit",
        "available_time",
        "buffer_time",
        "deadline",
        "completed_task_rescheduled",
    } <= names
