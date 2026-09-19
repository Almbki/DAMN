"""ReplanEvent domain entity.

Records *why* a plan changed. Kept as a first-class entity so future analysis
can study plan adaptation (trigger, reason, which tasks changed).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow
from app.domain.models.enums import ReplanTriggerType


class ReplanEvent(DomainModel):
    id: int | None = None
    plan_id: int
    trigger_type: ReplanTriggerType = ReplanTriggerType.MANUAL
    reason: str | None = None
    old_version: int = 1
    new_version: int = 2
    # Task ids whose schedule changed between the two versions.
    changed_tasks: list[int] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
