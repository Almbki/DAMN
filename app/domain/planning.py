"""Goal-level planning-mode derivation.

The product exposes four planning modes:

* ``one_off``          - a single deliverable
* ``recurring``        - one reusable action repeated on a cadence
* ``project``          - a finite curriculum / work-unit sequence
* ``project_recurring``- the same finite sequence advanced on a cadence

The LLM only classifies three semantic kinds (``one_off | recurring |
project``) plus an optional recurrence; ``project_recurring`` is the
deterministic combination of ``project`` + recurrence. This module is the one
place legacy ``goal_type`` / ``task_kind`` values are mapped to the four modes.
"""

from __future__ import annotations

from app.domain.models.enums import GoalType, PlanningMode, TaskKind
from app.domain.recurrence import RecurrenceFrequency

_RECURRING_MODES = frozenset(
    {PlanningMode.RECURRING, PlanningMode.PROJECT_RECURRING}
)


def derive_planning_mode(
    planning_mode: PlanningMode | str | None,
    *,
    goal_type: GoalType | str | None = None,
    task_kind: TaskKind | str | None = None,
    recurrence_frequency: RecurrenceFrequency | str | None = None,
    recurrence_weekdays: list[int] | None = None,
) -> PlanningMode:
    """Resolve the four-mode value from an explicit value or legacy fields.

    Explicit ``planning_mode`` always wins. Otherwise legacy rows are mapped
    conservatively so no existing goal changes behaviour after the migration.
    """
    if planning_mode is not None:
        return PlanningMode(planning_mode)

    kind = TaskKind(task_kind) if task_kind is not None else None
    goal = GoalType(goal_type) if goal_type is not None else None
    has_recurrence = recurrence_frequency is not None or bool(recurrence_weekdays)

    if kind is TaskKind.ONE_OFF:
        return PlanningMode.ONE_OFF
    if kind is TaskKind.ROUTINE:
        return PlanningMode.RECURRING
    if kind is TaskKind.LONG_TERM:
        # A long-term *project* with a rhythm is the 4th mode; a plain
        # long-term goal keeps the legacy recurring series behaviour.
        if goal is GoalType.PROJECT and has_recurrence:
            return PlanningMode.PROJECT_RECURRING
        if goal is GoalType.PROJECT:
            return PlanningMode.PROJECT
        return PlanningMode.RECURRING

    if goal is GoalType.PROJECT:
        return (
            PlanningMode.PROJECT_RECURRING
            if has_recurrence
            else PlanningMode.PROJECT
        )
    if goal in {GoalType.HABIT, GoalType.LONG_TERM}:
        return PlanningMode.RECURRING
    return PlanningMode.ONE_OFF


def derive_recurrence_frequency(
    planning_mode: PlanningMode | str,
    recurrence_frequency: RecurrenceFrequency | str | None = None,
    recurrence_weekdays: list[int] | None = None,
) -> RecurrenceFrequency | None:
    """Frequency for a recurring/project-recurring goal; ``None`` otherwise."""
    mode = PlanningMode(planning_mode)
    if mode not in _RECURRING_MODES:
        return None
    if recurrence_frequency is not None:
        try:
            return RecurrenceFrequency(recurrence_frequency)
        except ValueError:
            pass
    weekdays = sorted({int(day) for day in (recurrence_weekdays or [])})
    if weekdays and len(weekdays) < 7:
        return RecurrenceFrequency.WEEKLY
    return RecurrenceFrequency.DAILY


def derive_recurrence_interval(value: int | None) -> int:
    return max(1, int(value or 1))


__all__ = [
    "derive_planning_mode",
    "derive_recurrence_frequency",
    "derive_recurrence_interval",
]
