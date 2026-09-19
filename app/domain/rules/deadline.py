"""HARD: a task must never be scheduled after its deadline."""

from __future__ import annotations

from app.domain.models.enums import ViolationSeverity
from app.domain.rules.base import Rule, RuleContext, RuleViolation
from app.domain.scheduling.schedule_result import CandidateSchedule


class DeadlineRule(Rule):
    """HARD: ``scheduled_date <= task_deadlines[task_id]`` when a deadline exists."""

    name = "deadline"
    severity: ViolationSeverity = ViolationSeverity.HARD

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        for task in schedule.tasks:
            deadline = context.task_deadlines.get(task.task_id)
            if deadline is not None and task.scheduled_date > deadline:
                violations.append(
                    self._violation(
                        f"Task scheduled on {task.scheduled_date.isoformat()} is "
                        f"after its deadline {deadline.isoformat()}.",
                        task_ids=[task.task_id],
                        code="deadline_exceeded",
                    )
                )
        return violations