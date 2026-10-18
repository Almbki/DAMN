"""HARD: a task must never overlap an imported fixed calendar event."""

from __future__ import annotations

from datetime import date

from app.domain.models.enums import ViolationSeverity
from app.domain.rules.base import Rule, RuleContext, RuleViolation
from app.domain.scheduling.schedule_result import CandidateSchedule, FixedEvent


class FixedEventOverlapRule(Rule):
    """HARD: generated tasks and fixed events are mutually exclusive."""

    name = "fixed_event_overlap"
    severity: ViolationSeverity = ViolationSeverity.HARD

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        if not context.fixed_events:
            return []

        by_date: dict[date, list[FixedEvent]] = {}
        for event in context.fixed_events:
            by_date.setdefault(event.date, []).append(event)

        violations: list[RuleViolation] = []
        for task in schedule.tasks:
            for event in by_date.get(task.scheduled_date, []):
                if task.start_time < event.end_time and event.start_time < task.end_time:
                    title = f" '{event.title}'" if event.title else ""
                    violations.append(
                        self._violation(
                            f"Task {task.task_id} overlaps fixed event{title} on "
                            f"{task.scheduled_date.isoformat()} "
                            f"[{event.start_time.strftime('%H:%M')}, "
                            f"{event.end_time.strftime('%H:%M')}].",
                            task_ids=[task.task_id],
                            code="fixed_event_overlap",
                        )
                    )
                    break
        return violations


__all__ = ["FixedEventOverlapRule"]
