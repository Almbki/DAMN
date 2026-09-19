"""High cognitive-load hard constraints.

* Two ``CognitiveLoad.HIGH`` tasks must never be consecutive in time: there
  must either be at least one lighter task between them, or a gap of at least
  ``HIGH_GAP_MINUTES`` (30) minutes.
* A single day may hold at most ``context.high_cognitive_max_per_day`` HIGH
  tasks.
"""

from __future__ import annotations

from app.domain.models.enums import CognitiveLoad, ViolationSeverity
from app.domain.rules.base import Rule, RuleContext, RuleViolation
from app.domain.scheduling.schedule_result import CandidateSchedule

#: Minimum gap (minutes) between two consecutive HIGH tasks when no lighter
#: task sits between them.
HIGH_GAP_MINUTES = 30


def _minutes(t) -> int:  # type: ignore[type-arg]  # datetime.time
    return t.hour * 60 + t.minute  # type: ignore[union-attr,attr-defined]


class HighCognitiveNotConsecutiveRule(Rule):
    """HARD: high-cognitive tasks need spacing + a daily cap."""

    name = "high_cognitive_not_consecutive"
    severity: ViolationSeverity = ViolationSeverity.HARD

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        for day in schedule.days():
            tasks = sorted(schedule.tasks_on(day), key=lambda t: t.start_time)

            # (1) adjacency: two HIGH tasks next to each other with too small a gap.
            for prev, nxt in zip(tasks, tasks[1:], strict=False):
                if (
                    prev.cognitive_load == CognitiveLoad.HIGH
                    and nxt.cognitive_load == CognitiveLoad.HIGH
                ):
                    gap = _minutes(nxt.start_time) - _minutes(prev.end_time)
                    if gap < HIGH_GAP_MINUTES:
                        violations.append(
                            self._violation(
                                "Two high-cognitive tasks are consecutive with less "
                                f"than a {HIGH_GAP_MINUTES}-minute gap "
                                f"({gap} min on {day.isoformat()}); insert a lighter "
                                "task or a longer break between them.",
                                task_ids=[prev.task_id, nxt.task_id],
                                code="high_cognitive_consecutive",
                            )
                        )

            # (2) daily cap on HIGH tasks.
            high_ids = [
                t.task_id for t in tasks if t.cognitive_load == CognitiveLoad.HIGH
            ]
            if len(high_ids) > context.high_cognitive_max_per_day:
                violations.append(
                    self._violation(
                        f"{len(high_ids)} high-cognitive tasks on {day.isoformat()} "
                        f"exceed the daily maximum of "
                        f"{context.high_cognitive_max_per_day}.",
                        task_ids=high_ids,
                        code="high_cognitive_daily_max",
                    )
                )
        return violations