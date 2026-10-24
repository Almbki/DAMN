"""Application DTOs for the situation-trend report."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SituationTrendPointData(BaseModel):
    date: date
    energy: float | None = None
    stress: float | None = None
    efficacy: float | None = None


class SituationTrendData(BaseModel):
    points: list[SituationTrendPointData] = Field(default_factory=list)
    samples: int = 0
    min_samples: int = 0
    sufficient: bool = False
    drivers: list[str] = Field(default_factory=list)


__all__ = ["SituationTrendData", "SituationTrendPointData"]