"""Schedule import API schemas."""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field


class ScheduleEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    event_kind: str = "class"
    start_date: date | None = None
    end_date: date | None = None
    start_time: time
    end_time: time
    weekdays: list[int] | None = None
    source: str = "manual"
    external_uid: str | None = None
    location: str | None = None
    teacher: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ScheduleImportResult(BaseModel):
    """Outcome of a CSV/XLSX import.

    ``warnings`` lists per-row validation problems (invalid rows are skipped,
    never fatal) while ``conflicts`` reports overlaps inside the file and with
    the current plan. Conflicts never block the import.
    """

    imported: int = Field(default=0, ge=0)
    updated: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


__all__ = ["ScheduleEventRead", "ScheduleImportResult"]
