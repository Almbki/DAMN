"""Scheduling value objects.

These types form the contract between the Scheduler (produces a candidate
schedule), the Rule Engine (validates it) and the Plan service (persists it).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta

from pydantic import BaseModel, Field

from app.domain.models.enums import CognitiveLoad, Priority

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class FixedEvent:
    """A concrete immutable calendar interval (course, exam, busy block)."""

    date: date
    start_time: time
    end_time: time
    title: str = ""


class ScheduledTask(BaseModel):
    """A single task placed on the calendar."""

    task_id: int
    title: str = ""
    goal_id: int | None = None
    scheduled_date: date
    start_time: time
    end_time: time
    duration_minutes: int = Field(ge=1)
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM
    priority: Priority = Priority.MEDIUM
    completion_probability: float = Field(default=1.0, ge=0.0, le=1.0)
    is_flexible: bool = True
    #: Recurrence identity (copied from the Task); None for one-off work.
    series_id: str | None = None
    occurrence_date: date | None = None


class SchedulingFailure(BaseModel):
    """Structured deterministic reason for an unplaced task."""

    code: str = "UNKNOWN"
    needed_minutes: int | None = None
    available_minutes: int | None = None
    message: str = ""


class CandidateSchedule(BaseModel):
    """Output of the Scheduler, input of every Rule."""

    schema_version: str = SCHEMA_VERSION
    start_date: date
    end_date: date
    tasks: list[ScheduledTask] = Field(default_factory=list)
    # Tasks the scheduler could not place within the horizon.
    unscheduled_task_ids: list[int] = Field(default_factory=list)
    # task_id -> deterministic reason for the final placement failure.
    unscheduled_reasons: dict[int, SchedulingFailure] = Field(default_factory=dict)

    def tasks_on(self, day: date) -> list[ScheduledTask]:
        return [t for t in self.tasks if t.scheduled_date == day]

    def daily_minutes(self) -> dict[date, int]:
        totals: dict[date, int] = {}
        for task in self.tasks:
            totals[task.scheduled_date] = totals.get(task.scheduled_date, 0) + task.duration_minutes
        return totals

    def days(self) -> list[date]:
        span = (self.end_date - self.start_date).days
        return [self.start_date + timedelta(days=i) for i in range(max(span + 1, 1))]


__all__ = [
    "CandidateSchedule",
    "FixedEvent",
    "SCHEMA_VERSION",
    "ScheduledTask",
    "SchedulingFailure",
]
