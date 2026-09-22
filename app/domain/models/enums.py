"""Domain enums shared across models, rules and scheduling."""

from __future__ import annotations

from enum import Enum, StrEnum


class GoalType(StrEnum):
    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"
    PROJECT = "project"
    HABIT = "habit"
    OTHER = "other"


class GoalStatus(StrEnum):
    #: Waiting to be decomposed (frontend "待拆解清单"). Added for the
    #: frontend contract; stored as a string so no data migration is needed.
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


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
