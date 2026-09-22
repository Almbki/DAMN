"""Insight / analytics application DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DailyCompletion(BaseModel):
    date: str
    total_tasks: int = 0
    completed_tasks: int = 0
    completion_rate: float = 0.0
    planned_minutes: int = 0


class InsightReport(BaseModel):
    """Aggregated, read-only view of how the user is actually doing."""

    plan_id: int
    total_tasks: int = 0
    completed_tasks: int = 0
    completion_rate: float = 0.0
    total_planned_minutes: int = 0
    total_actual_minutes: int = 0
    avg_stress: float | None = None
    avg_energy: float | None = None
    high_cognitive_minutes: int = 0
    predicted_vs_actual_ratio: float | None = None
    cognitive_load_breakdown: dict[str, int] = Field(default_factory=dict)
    daily: list[DailyCompletion] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    #: {samples, min_samples, sufficient} - whether history backs these numbers.
    data_sufficiency: dict | None = None
    #: Human-readable reasons (Chinese UI copy).
    drivers: list[str] = Field(default_factory=list)
