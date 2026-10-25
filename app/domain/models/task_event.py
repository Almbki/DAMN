"""TaskEvent domain entity - one append-only task change record."""

from __future__ import annotations

from datetime import datetime

from app.domain.models.base import DomainModel, utcnow


class TaskEvent(DomainModel):
    id: int | None = None
    user_id: int
    task_id: int
    #: created / status_changed / edited / rescheduled / corrected / deleted
    event_type: str
    before: dict | None = None
    after: dict | None = None
    reason: str | None = None
    created_at: datetime = utcnow()


__all__ = ["TaskEvent"]
