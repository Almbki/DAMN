"""TaskDependency domain entity (hard/soft prerequisite)."""

from __future__ import annotations

from datetime import datetime

from app.domain.models.base import DomainModel, utcnow


class TaskDependency(DomainModel):
    id: int | None = None
    task_id: int
    depends_on_task_id: int
    #: hard (must be done first) / soft (preferred order only).
    dependency_type: str = "hard"
    created_at: datetime = utcnow()


__all__ = ["TaskDependency"]
