"""HARD: a task must never be scheduled before its earliest day.

Long-term / routine goals are split into one occurrence per day; each occurrence
must land on (or after) its own occurrence date instead of being pulled forward.
"""

from __future__ import annotations

from app.domain.models.enums import ViolationSeverity
from app.domain.rules.base import Rule, RuleContext, RuleViolation
from app.domain.scheduling.schedule_result import CandidateSchedule


class EarliestStartRule(Rule):
    """HARD: ``scheduled_date >= task_earliest_dates[task_id]`` when present."""

    name = "earliest_start"
    severity: ViolationSeverity = ViolationSeverity.HARD

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        for task in schedule.tasks:
            earliest = context.task_earliest_dates.get(task.task_id)
            if earliest is not None and task.scheduled_date < earliest:
                violations.append(
                    self._violation(
                        f"Task scheduled on {task.scheduled_date.isoformat()} is "
                        f"before its earliest date {earliest.isoformat()}.",
                        task_ids=[task.task_id],
                        code="earliest_start",
                    )
                )
        return violations
