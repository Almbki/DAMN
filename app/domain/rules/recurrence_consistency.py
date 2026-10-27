"""HARD: a materialized recurrence series must be internally consistent.

This is the fail-closed guard for the long-term scheduling contract:

* every occurrence must sit on its declared ``occurrence_date``;
* one series may have at most one occurrence per date;
* an occurrence must stay inside the goal's ``[start_date, end_date]``;
* the materialized set must equal the set implied by the recurrence rule
  (no silently truncated series).
"""

from __future__ import annotations

from app.domain.models.enums import ViolationSeverity
from app.domain.recurrence import RecurrenceError, RecurrenceRule
from app.domain.rules.base import Rule, RuleContext, RuleViolation
from app.domain.scheduling.schedule_result import CandidateSchedule


class RecurrenceConsistencyRule(Rule):
    """HARD: duplicate / wrong-day / out-of-range / incomplete occurrences."""

    name = "recurrence_consistency"
    severity: ViolationSeverity = ViolationSeverity.HARD

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []

        seen: dict[tuple[str, object], int] = {}
        for task in schedule.tasks:
            if not task.series_id or task.occurrence_date is None:
                continue
            spec = context.series_specs.get(task.series_id)
            if spec is not None and not (
                spec.start_date <= task.occurrence_date <= spec.end_date
            ):
                violations.append(
                    self._violation(
                        f"Series {task.series_id} occurrence "
                        f"{task.occurrence_date.isoformat()} is outside "
                        f"[{spec.start_date.isoformat()}, "
                        f"{spec.end_date.isoformat()}].",
                        task_ids=[task.task_id],
                        code="recurrence_out_of_range",
                    )
                )
            if task.scheduled_date != task.occurrence_date:
                violations.append(
                    self._violation(
                        f"Series {task.series_id} occurrence "
                        f"{task.occurrence_date.isoformat()} was scheduled on "
                        f"{task.scheduled_date.isoformat()}.",
                        task_ids=[task.task_id],
                        code="recurrence_wrong_day",
                    )
                )
            key = (task.series_id, task.occurrence_date)
            if key in seen:
                violations.append(
                    self._violation(
                        f"Series {task.series_id} has duplicate occurrences on "
                        f"{task.occurrence_date.isoformat()}.",
                        task_ids=[seen[key], task.task_id],
                        code="recurrence_duplicate",
                    )
                )
            else:
                seen[key] = task.task_id

        # Completeness is checked against the declared rule, not the scheduled
        # subset: an occurrence that could not be placed still exists as a row.
        for series_id, spec in context.series_specs.items():
            try:
                expected = set(
                    RecurrenceRule(
                        frequency=spec.frequency,
                        start_date=spec.start_date,
                        end_date=spec.end_date,
                        interval=spec.interval,
                        weekdays=tuple(spec.weekdays),
                    ).occurrences()
                )
            except RecurrenceError as exc:
                violations.append(
                    self._violation(
                        f"Series {series_id} cannot be expanded: {exc}",
                        code="recurrence_invalid",
                    )
                )
                continue

            actual = context.series_occurrences.get(series_id, set())
            missing = sorted(expected - actual)
            if missing:
                violations.append(
                    self._violation(
                        f"Series {series_id} is missing {len(missing)} "
                        f"occurrence(s); first missing "
                        f"{missing[0].isoformat()}.",
                        code="recurrence_incomplete",
                    )
                )
            unexpected = sorted(actual - expected)
            if unexpected:
                violations.append(
                    self._violation(
                        f"Series {series_id} has {len(unexpected)} unexpected "
                        f"occurrence(s); first "
                        f"{unexpected[0].isoformat()}.",
                        code="recurrence_unexpected",
                    )
                )

        return violations


__all__ = ["RecurrenceConsistencyRule"]
