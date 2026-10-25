"""Daily scheduling value objects.

The scheduler emits one DailyPlan per day in its horizon so the plan
service (or the UI) can explain why a day looks the way it does, and one
UnscheduledTask per task it could not place.

These are pure domain value objects: no ORM, no rule engine, no LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

#: Machine-readable ``UnscheduledTask.reason`` codes.
REASON_CAPACITY = "capacity"
REASON_DEADLINE = "deadline"
REASON_LONG_TERM_WAIT = "long_term_wait"
REASON_NO_SLOT = "no_slot"


@dataclass(frozen=True)
class DailyPlan:
    """One day's allocation produced by the scheduler.

    ``capacity_minutes`` is the *physical* capacity of the day after fixed
    events and the daily limit (before the burst reserve, which is a packing
    policy); ``used_minutes`` is what the scheduler placed on it.
    """

    date: date
    capacity_minutes: int
    used_minutes: int = 0
    task_ids: list[int] = field(default_factory=list)
    #: Human-readable capacity rationale (limits, fixed events, reserves).
    reasons: list[str] = field(default_factory=list)

    @property
    def remaining_minutes(self) -> int:
        return max(self.capacity_minutes - self.used_minutes, 0)


@dataclass(frozen=True)
class UnscheduledTask:
    """A task the scheduler could not place, with the day it gave up on."""

    task_id: int
    date: date
    reason: str


__all__ = [
    "REASON_CAPACITY",
    "REASON_DEADLINE",
    "REASON_LONG_TERM_WAIT",
    "REASON_NO_SLOT",
    "DailyPlan",
    "UnscheduledTask",
]
