"""Plan domain entity.

A plan is always one immutable version. Replanning never mutates an existing
plan: it creates a new ``Plan`` row (version + 1) and marks the previous one as
``SUPERSEDED``. The link between versions is captured by ``parent_plan_id`` and
by :class:`app.domain.models.user_model.ReplanEvent`.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow
from app.domain.models.enums import PlanStatus


class Plan(DomainModel):
    id: int | None = None
    user_id: int
    version: int = 1
    status: PlanStatus = PlanStatus.DRAFT
    title: str | None = None
    start_date: date
    end_date: date
    parent_plan_id: int | None = None
    # Snapshot of the planner confidence for this version (0..1).
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utcnow)
