"""ScheduleEvent domain entity.

A user-imported fixed calendar event (course, exam, busy block). The scheduler
and the rule engine treat these as immovable: generated tasks must never
overlap them.
"""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow

#: Allowed ``event_kind`` values (stored as a plain string, not an enum, so a
#: future kind does not require a migration).
EVENT_KINDS = ("class", "exam", "busy", "other")
#: Allowed import sources.
EVENT_SOURCES = ("csv", "xlsx", "manual")


class ScheduleEvent(DomainModel):
    id: int | None = None
    user_id: int
    title: str
    event_kind: str = "class"
    #: Optional bounds of the recurrence. ``None`` means open-ended.
    start_date: date | None = None
    end_date: date | None = None
    start_time: time
    end_time: time
    #: 0=Monday .. 6=Sunday. ``None`` means a one-off event on ``start_date``.
    weekdays: list[int] | None = None
    source: str = "manual"
    #: Stable import identity (CSV/XLSX uid or a hash of the normalized fields).
    external_uid: str | None = None
    location: str | None = None
    teacher: str | None = None
    notes: str | None = None
    deleted_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


__all__ = ["EVENT_KINDS", "EVENT_SOURCES", "ScheduleEvent"]
