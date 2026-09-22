"""Feedback API schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.enums import TimeOfDay
from app.schemas.plan import FeedbackAdjustmentRead, ReplanEligibilityRead


class FeedbackCreate(BaseModel):
    date: date
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    stress_level: int | None = Field(default=None, ge=0, le=10)
    energy_level: int | None = Field(default=None, ge=0, le=10)
    delay_reason: str | None = Field(default=None, max_length=500)
    free_text: str | None = Field(default=None, max_length=2000)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    dominant_time_of_day: TimeOfDay | None = None


class FeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    plan_id: int
    date: date
    completion_rate: float
    stress_level: int | None = None
    energy_level: int | None = None
    delay_reason: str | None = None
    free_text: str | None = None
    sleep_hours: float | None = None
    dominant_time_of_day: TimeOfDay | None = None
    created_at: datetime


class FeedbackSubmitResponse(BaseModel):
    feedback: FeedbackRead
    replan_triggered: bool = False
    replan_plan_id: int | None = None
    replan_eligibility: ReplanEligibilityRead | None = None
    #: Agent decision from the feedback loop (route / severity / reasons).
    adjustment: FeedbackAdjustmentRead | None = None
