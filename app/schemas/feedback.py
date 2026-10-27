"""Feedback API schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.models.enums import FeedbackObligationStatus, TimeOfDay
from app.schemas.plan import FeedbackAdjustmentRead, ReplanEligibilityRead


class TaskReason(BaseModel):
    """Why one specific unfinished task was not completed today."""

    task_id: int
    reason: str = Field(max_length=32)
    note: str | None = Field(default=None, max_length=500)


class FeedbackCreate(BaseModel):
    date: date
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    stress_level: int | None = Field(default=None, ge=0, le=10)
    energy_level: int | None = Field(default=None, ge=0, le=10)
    delay_reason: str | None = Field(default=None, max_length=500)
    task_reasons: list[TaskReason] = Field(default_factory=list)
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
    task_reasons: list[TaskReason] = Field(default_factory=list)
    free_text: str | None = None
    sleep_hours: float | None = None
    dominant_time_of_day: TimeOfDay | None = None
    created_at: datetime

    @field_validator("task_reasons", mode="before")
    @classmethod
    def _null_task_reasons(cls, value: object) -> object:
        """Older rows persisted before the column existed hold ``NULL``."""
        return [] if value is None else value


class FeedbackObligationRead(BaseModel):
    """One unresolved daily-feedback debt (user + execution date)."""

    execution_date: date
    status: FeedbackObligationStatus = FeedbackObligationStatus.PENDING
    #: True when the obligation belongs to a day before "today".
    is_retrospective: bool = False
    #: Plan the client should submit the historical check-in against.
    plan_id: int | None = None


class FeedbackSubmitResponse(BaseModel):
    feedback: FeedbackRead
    replan_triggered: bool = False
    replan_plan_id: int | None = None
    #: Set when `?stream_replan=true` was used: poll/stream this job for the
    #: feedback-driven replan result.
    replan_job_id: str | None = None
    replan_eligibility: ReplanEligibilityRead | None = None
    #: Agent decision from the feedback loop (route / severity / reasons).
    adjustment: FeedbackAdjustmentRead | None = None
    #: Service-level policy route: "none" / "micro_adjust" / "full_replan".
    replan_decision: str = "none"
    #: Why the policy chose that route (or the graph's reason when it ran).
    replan_reason: str | None = None
