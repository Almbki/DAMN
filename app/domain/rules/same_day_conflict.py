"""HARD: subjects that must not share a single day.

``RuleContext.conflicting_subject_pairs`` holds subject pairs that compete for
the same cognitive attention. A day is invalid as soon as it contains tasks of
*both* subjects (case-insensitive). Example default: ``("math", "algorithm")``.
"""

from __future__ import annotations

from app.domain.models.enums import ViolationSeverity
from app.domain.rules.base import Rule, RuleContext, RuleViolation
from app.domain.scheduling.schedule_result import CandidateSchedule


class SameDayConflictRule(Rule):
    """HARD: conflicting subjects must not share a day."""

    name = "same_day_conflict"
    severity: ViolationSeverity = ViolationSeverity.HARD

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        pairs = sorted(
            {(a.strip().lower(), b.strip().lower()) for a, b in context.conflicting_subject_pairs}
        )
        if not pairs:
            return violations

        for day in schedule.days():
            # subject(lower) -> task_ids placed that day.
            subjects_on_day: dict[str, list[int]] = {}
            for task in schedule.tasks_on(day):
                subject = context.task_subjects.get(task.task_id)
                if subject:
                    subjects_on_day.setdefault(subject.strip().lower(), []).append(
                        task.task_id
                    )
            for a, b in pairs:
                if a in subjects_on_day and b in subjects_on_day:
                    task_ids = subjects_on_day[a] + subjects_on_day[b]
                    violations.append(
                        self._violation(
                            f"Conflicting subjects '{a}' and '{b}' both appear on "
                            f"{day.isoformat()}.",
                            task_ids=task_ids,
                            code="same_day_conflict",
                        )
                    )
        return violations