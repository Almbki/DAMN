"""Domain enums shared across models, rules and scheduling."""

from __future__ import annotations

from enum import Enum, StrEnum


class GoalType(StrEnum):
    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"
    PROJECT = "project"
    HABIT = "habit"
    OTHER = "other"


class TaskKind(StrEnum):
    """How a task *instance* behaves (legacy storage name).

    ``ONE_OFF`` is a single task row; ``LONG_TERM`` and ``ROUTINE`` are series
    occurrence rows. Goal-level planning uses :class:`PlanningMode` instead.
    """

    ONE_OFF = "one_off"
    LONG_TERM = "long_term"
    ROUTINE = "routine"


class PlanningMode(StrEnum):
    """Goal-level planning mode shown in the UI and stored on ``goals``.

    ``PROJECT_RECURRING`` means "project content advances on a recurrence
    cadence": the finite work-unit sequence is paired with occurrence dates.
    It is the product-level 4th type; the LLM still classifies it as
    ``goal_kind=project`` + a non-null ``recurrence``.
    """

    ONE_OFF = "one_off"
    RECURRING = "recurring"
    PROJECT = "project"
    PROJECT_RECURRING = "project_recurring"


class GoalStatus(StrEnum):
    #: Waiting to be decomposed (frontend "待拆解清单"). Added for the
    #: frontend contract; stored as a string so no data migration is needed.
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


class GoalSetStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class CognitiveLoad(StrEnum):
    """How much focused cognitive capacity a task consumes.

    ``RESTORATIVE`` = activities used as cognitive breaks (exercise, music).
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    RESTORATIVE = "restorative"


class Priority(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ReplanTriggerType(StrEnum):
    MANUAL = "manual"
    FEEDBACK_TRIGGERED = "feedback_triggered"
    SCHEDULED = "scheduled"
    SYSTEM = "system"


class ViolationSeverity(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class TimeOfDay(StrEnum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


class LoadLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    OVERLOADED = "overloaded"
