"""Hard-constraint rule engine contract.

Design::

    Rule -> validate(schedule, context) -> RuleViolation[]

The rule engine is the *only* authority on hard constraints. LLM output never
decides whether a constraint is satisfied - it only produces candidate plans
that must pass through here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, time
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.domain.models.enums import ViolationSeverity

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.scheduling.schedule_result import CandidateSchedule


class RuleViolation(BaseModel):
    """Structured violation returned by every rule.

    Matches the agreed wire shape::

        {"rule": "...", "severity": "hard", "task_ids": [], "message": "..."}
    """

    rule: str
    severity: ViolationSeverity = ViolationSeverity.HARD
    task_ids: list[int] = Field(default_factory=list)
    message: str = ""
    # Optional machine readable code for automated repair.
    code: str | None = None

    @property
    def is_hard(self) -> bool:
        return self.severity == ViolationSeverity.HARD


class RuleContext(BaseModel):
    """Everything a rule needs beyond the schedule itself.

    Built by the Plan service from the domain entities and user preferences.
    """

    daily_limit_minutes: int = Field(default=300, ge=1)
    buffer_minutes: int = Field(default=15, ge=0)
    high_cognitive_max_per_day: int = Field(default=2, ge=1)
    # Hard cap of usable minutes per single day.
    available_minutes_per_day: int = Field(default=480, ge=1)
    day_start: time = time(8, 0)
    day_end: time = time(22, 0)
    # task_id -> normalised subject tag (e.g. "math", "algorithm").
    task_subjects: dict[int, str] = Field(default_factory=dict)
    # task_id -> hard deadline (exclusive upper bound: cannot be scheduled after).
    task_deadlines: dict[int, date] = Field(default_factory=dict)
    # Tasks already completed must never be re-scheduled.
    completed_task_ids: set[int] = Field(default_factory=set)
    # Subjects that must not share the same day, e.g. [("math", "algorithm")].
    conflicting_subject_pairs: list[tuple[str, str]] = Field(
        default_factory=lambda: [("math", "algorithm")]
    )


class Rule(ABC):
    """A single hard/soft scheduling constraint."""

    name: str = "rule"
    severity: ViolationSeverity = ViolationSeverity.HARD

    @abstractmethod
    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        """Return every violation of this rule. Empty list == satisfied."""

    # Convenience for rules that emit multiple findings.
    def _violation(
        self,
        message: str,
        *,
        task_ids: list[int] | None = None,
        code: str | None = None,
        severity: ViolationSeverity | None = None,
    ) -> RuleViolation:
        return RuleViolation(
            rule=self.name,
            severity=severity or self.severity,
            task_ids=task_ids or [],
            message=message,
            code=code,
        )


class RuleEngine:
    """Runs a list of rules over a candidate schedule."""

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self._rules: list[Rule] = list(rules) if rules is not None else default_rules()

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)

    def register(self, rule: Rule) -> None:
        self._rules.append(rule)

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        for rule in self._rules:
            violations.extend(rule.validate(schedule, context))
        return violations

    def hard_violations(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        return [v for v in self.validate(schedule, context) if v.is_hard]

    def is_valid(self, schedule: CandidateSchedule, context: RuleContext) -> bool:
        return not self.hard_violations(schedule, context)


def default_rules() -> list[Rule]:
    """Build the first-version rule set.

    Imported lazily to avoid import cycles between ``base`` and the concrete
    rule modules.
    """
    from app.domain.rules.buffer_time import BufferTimeRule
    from app.domain.rules.cognitive_load import HighCognitiveNotConsecutiveRule
    from app.domain.rules.completed_tasks import CompletedTaskRule
    from app.domain.rules.daily_limit import AvailableTimeRule, DailyLimitRule
    from app.domain.rules.deadline import DeadlineRule
    from app.domain.rules.same_day_conflict import SameDayConflictRule

    return [
        HighCognitiveNotConsecutiveRule(),
        SameDayConflictRule(),
        DailyLimitRule(),
        AvailableTimeRule(),
        BufferTimeRule(),
        DeadlineRule(),
        CompletedTaskRule(),
    ]
