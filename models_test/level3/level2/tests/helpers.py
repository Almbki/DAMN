from __future__ import annotations

import copy
from datetime import date, datetime, timedelta

from ddsr.schemas import (
    DayInput,
    ReflectionInput,
    TaskExecution,
    TaskPlan,
)


def trait_profile(theta: float = 0.0, se: float = 0.30) -> dict:
    return {
        "schema_version": "1.0",
        "model": "trait_v1",
        "instrument": "IPIP-NEO-120",
        "method": "bayesian_cat",
        "calibration": {
            "model": "samejima_grm",
            "version": "grm_v1",
            "reference_population": "Johnson_IPIP_NEO_120",
        },
        "domains": {
            domain: {
                "theta": theta,
                "se": se,
                "ci95": [-0.6, 0.6],
                "items_answered": 8,
            }
            for domain in "NEOAC"
        },
        "assessment": {"total_items_answered": 40, "completed": True},
    }


def plan(
    task_id: str = "t1",
    *,
    day: date = date(2026, 10, 20),
    hour: int = 9,
    duration: int = 60,
    difficulty: int | None = 3,
) -> TaskPlan:
    return TaskPlan(
        task_id=task_id,
        title=f"task {task_id}",
        planned_start=datetime(day.year, day.month, day.day, hour, 0),
        estimated_duration_minutes=duration,
        difficulty=difficulty,
    )


def execution(
    task_id: str = "t1",
    *,
    day: date = date(2026, 10, 20),
    start_hour: int | None = 9,
    start_minute: int = 0,
    duration: float | None = 60,
    completion: float | None = 1.0,
    completed: bool = True,
    interruptions: int = 0,
) -> TaskExecution:
    actual_start = (
        datetime(day.year, day.month, day.day, start_hour, start_minute)
        if start_hour is not None
        else None
    )
    return TaskExecution(
        task_id=task_id,
        actual_start=actual_start,
        actual_duration_minutes=duration,
        completion_ratio=completion,
        completed=completed,
        interruption_count=interruptions,
    )


def day(
    day_date: date = date(2026, 10, 20),
    *,
    plans: list[TaskPlan] | None = None,
    executions: list[TaskExecution] | None = None,
    reflection: ReflectionInput | None = None,
    passive_context=None,
) -> DayInput:
    return DayInput(
        date=day_date,
        task_plans=plans or [],
        task_executions=executions or [],
        reflection=reflection,
        passive_context=passive_context,
    )


def next_day(value: date, n: int = 1) -> date:
    return value + timedelta(days=n)


def deep_copy(profile: dict) -> dict:
    return copy.deepcopy(profile)
