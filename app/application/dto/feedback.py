"""Feedback-related application DTOs."""

from __future__ import annotations

from pydantic import BaseModel

from app.application.dto.agent import FeedbackCycleOutcome
from app.application.dto.replan import ReplanEligibility
from app.domain.models import Feedback


class FeedbackSubmitResult(BaseModel):
    feedback: Feedback
    replan_triggered: bool = False
    replan_plan_id: int | None = None
    replan_eligibility: ReplanEligibility | None = None
    #: Agent decision from the feedback loop (route / severity / reasons).
    adjustment: FeedbackCycleOutcome | None = None
