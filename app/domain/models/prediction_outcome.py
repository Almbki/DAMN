"""PredictionOutcome domain entity - the observed result of one prediction."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow


class PredictionOutcome(DomainModel):
    id: int | None = None
    snapshot_id: int
    task_id: int
    completed: bool = False
    completion_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    actual_duration_minutes: float | None = Field(default=None, ge=0.0)
    outcome_timestamp: datetime | None = None
    notes: str | None = None
    #: execution / manual
    source: str = "execution"
    created_at: datetime = utcnow()


__all__ = ["PredictionOutcome"]
