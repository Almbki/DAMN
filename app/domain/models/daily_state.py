"""DailyState domain entity - one Level-2 state snapshot per user per day."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow


class DailyState(DomainModel):
    id: int | None = None
    user_id: int
    date: date
    fatigue: float = Field(ge=0.0, le=1.0)
    stress: float = Field(ge=0.0, le=1.0)
    self_efficacy: float = Field(ge=0.0, le=1.0)
    fatigue_uncertainty: float = Field(ge=0.0)
    stress_uncertainty: float = Field(ge=0.0)
    self_efficacy_uncertainty: float = Field(ge=0.0)
    evidence_availability: str = "none"
    evidence_count: int = Field(default=0, ge=0)
    conflict: bool = False
    next_day_prior: dict | None = None
    next_day_uncertainty: dict | None = None
    cold_start: bool = False
    gap_days: int = Field(default=0, ge=0)
    #: Full auditable DynamicStateProfile JSON.
    profile_json: dict | None = None
    model_version: str = ""
    config_version: str = ""
    artifact_hash: str = ""
    #: real | synthetic
    data_origin: str = "real"
    created_at: datetime = utcnow()


__all__ = ["DailyState"]
