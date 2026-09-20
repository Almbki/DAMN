"""Replan-related application DTOs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.domain.models import Plan
from app.domain.models.enums import ReplanTriggerType


class ReplanEligibility(BaseModel):
    """Answer to "can this plan be replanned right now?"."""

    eligible: bool
    reason: str = ""
    next_eligible_at: datetime | None = None
    last_replan_at: datetime | None = None
    cooldown_hours: int = 0


class ReplanResult(BaseModel):
    plan: Plan
    old_version: int
    new_version: int
    changed_task_ids: list[int] = Field(default_factory=list)
    reason: str = ""
    trigger_type: ReplanTriggerType = ReplanTriggerType.MANUAL


class ReplanTrigger(StrEnum):
    """Kept for API enum clarity (mirrors ReplanTriggerType)."""

    MANUAL = "manual"
    FEEDBACK_TRIGGERED = "feedback_triggered"
    SCHEDULED = "scheduled"
    SYSTEM = "system"
