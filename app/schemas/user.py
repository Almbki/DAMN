"""User API schemas."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

__all__ = [
    "DataSufficiency",
    "EstimateAccuracyPoint",
    "SchedulingPreferences",
    "SituationTrendPoint",
    "SituationTrendRead",
    "UserRead",
    "UserUpdate",
]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str | None = None
    execution_weight: float = 0.5
    profile: dict[str, Any] = Field(default_factory=dict)
    #: Portrait fields (see app/schemas/profile.py).
    identity: str | None = None
    #: Level 1 TraitProfileV1 JSON (authoritative stable traits).
    trait_profile: dict[str, Any] | None = None
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    execution_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    profile: dict[str, Any] | None = None
    # --- user portrait (see app/schemas/profile.py) ---
    identity: str | None = Field(default=None, max_length=200)
    #: Optional validated Level 1 trait profile (e.g. produced by the CAT).
    trait_profile: dict[str, Any] | None = None


class SchedulingPreferences(BaseModel):
    """Scheduling settings, stored on their own column.

    Matches the frontend contract: the four caps are required (they have
    defaults when omitted), ``sleep_start``/``sleep_end`` are ``HH:MM`` strings
    used by the UI (the scheduler does not consume them yet).
    """

    available_minutes_per_day: int = Field(default=480, ge=30, le=1440)
    daily_limit_minutes: int = Field(default=300, ge=30, le=1440)
    buffer_minutes: int = Field(default=15, ge=0, le=120)
    high_cognitive_max_per_day: int = Field(default=2, ge=1, le=10)
    sleep_start: str | None = Field(default=None, examples=["23:30"])
    sleep_end: str | None = Field(default=None, examples=["07:00"])
    #: Daily feedback reminder ("HH:MM", 24h). Defaults to the end-of-day prompt.
    feedback_time: str | None = Field(default="22:00", examples=["22:00"])
    #: Whether the daily feedback reminder is enabled (default on).
    feedback_enabled: bool = True

    @field_validator("sleep_start", "sleep_end", "feedback_time")
    @classmethod
    def _validate_hhmm(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        try:
            hour, minute = value.strip().split(":", 1)
            parsed = time(int(hour), int(minute))
        except (ValueError, TypeError) as exc:
            raise ValueError("expected HH:MM") from exc
        return parsed.strftime("%H:%M")


class EstimateAccuracyPoint(BaseModel):
    """One day of ``GET /users/me/estimate-accuracy`` (planned vs actual)."""

    date: date
    planned_minutes: int = 0
    actual_minutes: int = 0
    #: actual / planned; ``None`` when nothing was planned that day.
    ratio: float | None = None


class SituationTrendPoint(BaseModel):
    """One day of the profile trend (missing values are ``null``)."""

    date: date
    energy: float | None = Field(default=None, ge=0, le=10)
    stress: float | None = Field(default=None, ge=0, le=10)
    #: Efficacy = 0.6 * execution_weight + 0.4 * recent completion rate.
    efficacy: float | None = Field(default=None, ge=0.0, le=1.0)


class DataSufficiency(BaseModel):
    """Whether there is enough history to trust a derived signal."""

    samples: int = 0
    min_samples: int = 0
    sufficient: bool = False


class SituationTrendRead(BaseModel):
    """``GET /users/me/situation/trends`` - the profile page's curve + reasons."""

    points: list[SituationTrendPoint] = Field(default_factory=list)
    samples: int = 0
    min_samples: int = 0
    sufficient: bool = False
    #: Human-readable "why the system says this" sentences (Chinese UI copy).
    drivers: list[str] = Field(default_factory=list)
