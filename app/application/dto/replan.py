"""Replan application DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReplanEligibility(BaseModel):
    """Answer to "can this user replan right now?" (per-user cooldown)."""

    eligible: bool
    reason: str = ""
    next_eligible_at: datetime | None = None
    last_replan_at: datetime | None = None
    cooldown_hours: int = 0


__all__ = ["ReplanEligibility"]
