"""HARD: daily workload caps.

* ``DailyLimitRule``: total scheduled minutes per day <= ``daily_limit_minutes``.
* ``AvailableTimeRule``: total scheduled minutes per day <=
  ``available_minutes_per_day`` (hard usable capacity) and every task must sit
  inside the ``[day_start, day_end]`` window.
"""

from __future__ import annotations

from app.domain.models.enums import ViolationSeverity
from app.domain.rules.base import Rule, RuleContext, RuleViolation
from app.domain.scheduling.schedule_result import CandidateSchedule


class DailyLimitRule(Rule):
    """HARD: a day's total minutes must respect the daily limit."""

    name = "daily_limit"
    severity: ViolationSeverity = ViolationSeverity.HARD

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        for day, minutes in schedule.daily_minutes().items():
            if minutes > context.daily_limit_minutes:
                task_ids = [t.task_id for t in schedule.tasks_on(day)]
                violations.append(
                    self._violation(
                        f"Day {day.isoformat()} is over capacity: {minutes} minutes "
                        f"scheduled but the daily limit is "
                        f"{context.daily_limit_minutes} minutes.",
                        task_ids=task_ids,
                        code="daily_limit",
                    )
                )
        return violations


class AvailableTimeRule(Rule):
    """HARD: runtime capacity + available daily window."""

    name = "available_time"
    severity: ViolationSeverity = ViolationSeverity.HARD

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        # Per-day total must fit the hard usable minutes.
        for day, minutes in schedule.daily_minutes().items():
            if minutes > context.available_minutes_per_day:
                task_ids = [t.task_id for t in schedule.tasks_on(day)]
                violations.append(
                    self._violation(
                        f"Day {day.isoformat()} needs {minutes} minutes, more than "
                        f"the available {context.available_minutes_per_day} minutes.",
                        task_ids=task_ids,
                        code="available_time",
                    )
                )
        # Every task must sit inside the usable window.
        for task in schedule.tasks:
            # start >= end is defensive: such a task has no usable window at all.
            if (
                task.start_time < context.day_start
                or task.end_time > context.day_end
                or task.start_time >= task.end_time
            ):
                violations.append(
                    self._violation(
                        "Task falls outside the available daily window "
                        f"[{context.day_start.isoformat()}, "
                        f"{context.day_end.isoformat()}].",
                        task_ids=[task.task_id],
                        code="outside_available_window",
                    )
                )
        return violations