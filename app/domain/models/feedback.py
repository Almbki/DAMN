"""Feedback domain entity (daily quick check-in)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow
from app.domain.models.enums import TimeOfDay


class Feedback(DomainModel):
    id: int | None = None
    user_id: int
    plan_id: int
    date: date
    # 0..1 fraction of the day's tasks completed.
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    # 0..10 self report.
    stress_level: int | None = Field(default=None, ge=0, le=10)
    energy_level: int | None = Field(default=None, ge=0, le=10)
    delay_reason: str | None = None
    free_text: str | None = None
    # Optional context used as ML features later.
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    dominant_time_of_day: TimeOfDay | None = None
    created_at: datetime = Field(default_factory=utcnow)
