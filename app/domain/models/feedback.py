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
    #: Per-unfinished-task reasons (``[{task_id, reason, note?}, ...]``).
    #: Stored for analysis only; never used to route the replan policy.
    task_reasons: list[dict] | None = None
    free_text: str | None = None
    # --- Four-section optional reflection (A/B/C/D; free_text kept) ---
    day_review: str | None = None
    stuck_points: str | None = None
    state_review: str | None = None
    tomorrow_outlook: str | None = None
    #: Set once the end-of-day prompt was answered ("no more pings today").
    day_closed_at: datetime | None = None
    # Optional context used as ML features later.
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    dominant_time_of_day: TimeOfDay | None = None
    #: real | synthetic - provenance for training/evaluation isolation.
    data_origin: str = "real"
    created_at: datetime = Field(default_factory=utcnow)
