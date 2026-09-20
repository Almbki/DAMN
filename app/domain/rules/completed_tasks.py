"""HARD: completed tasks must never be re-scheduled."""

from __future__ import annotations

from app.domain.models.enums import ViolationSeverity
from app.domain.rules.base import Rule, RuleContext, RuleViolation
from app.domain.scheduling.schedule_result import CandidateSchedule


class CompletedTaskRule(Rule):
    """HARD: no scheduled task may appear in ``context.completed_task_ids``."""

    name = "completed_task_rescheduled"
    severity: ViolationSeverity = ViolationSeverity.HARD

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        for task in schedule.tasks:
            if task.task_id in context.completed_task_ids:
                violations.append(
                    self._violation(
                        "Completed tasks must never be scheduled.",
                        task_ids=[task.task_id],
                        code="completed_task_rescheduled",
                    )
                )
        return violations