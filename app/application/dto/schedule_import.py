"""Application DTO for timetable imports."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScheduleImportData(BaseModel):
    imported: int = Field(default=0, ge=0)
    updated: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


__all__ = ["ScheduleImportData"]