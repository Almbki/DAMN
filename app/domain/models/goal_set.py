"""Goal set domain entity (目标集).

A goal set groups goals created together (for example one plan-generation
batch) so the frontend can present them as a single collection and archive /
restore them together.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow
from app.domain.models.enums import GoalSetStatus


class GoalSet(DomainModel):
    id: int | None = None
    user_id: int
    name: str
    description: str | None = None
    status: GoalSetStatus = GoalSetStatus.ACTIVE
    archived_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)


__all__ = ["GoalSet"]
