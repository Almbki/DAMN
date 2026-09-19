"""HARD: mandatory buffer between tasks on the same day.

Tasks on the same day are ordered by start time. Between *every* adjacent pair
the gap ``next.start - prev.end`` must be at least ``context.buffer_minutes``.
Overlaps (negative gap) are violations as well.
"""

from __future__ import annotations

from app.domain.models.enums import ViolationSeverity
from app.domain.rules.base import Rule, RuleContext, RuleViolation
from app.domain.scheduling.schedule_result import CandidateSchedule


def _minutes(t) -> int:  # type: ignore[type-arg]  # datetime.time
    return t.hour * 60 + t.minute  # type: ignore[union-attr,attr-defined]


class BufferTimeRule(Rule):
    """HARD: adjacent same-day tasks need buffer (or must not overlap)."""

    name = "buffer_time"
    severity: ViolationSeverity = ViolationSeverity.HARD

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        for day in schedule.days():
            tasks = sorted(schedule.tasks_on(day), key=lambda t: t.start_time)
            for prev, nxt in zip(tasks, tasks[1:], strict=False):
                gap = _minutes(nxt.start_time) - _minutes(prev.end_time)
                if gap < context.buffer_minutes:
                    if gap < 0:
                        message = (
                            f"Tasks overlap by {-gap} minutes on {day.isoformat()}."
                        )
                    else:
                        message = (
                            f"Insufficient buffer on {day.isoformat()}: only "
                            f"{gap} minute(s) between tasks, "
                            f"{context.buffer_minutes} required."
                        )
                    violations.append(
                        self._violation(
                            message,
                            task_ids=[prev.task_id, nxt.task_id],
                            code="insufficient_buffer",
                        )
                    )
        return violations