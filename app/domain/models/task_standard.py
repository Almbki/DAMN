"""TaskStandard domain entity (quantifiable "definition of done")."""

from __future__ import annotations

from pydantic import Field

from app.domain.models.base import DomainModel


class TaskStandard(DomainModel):
    id: int | None = None
    task_id: int
    description: str
    # Minutes.
    estimated_duration: int = Field(default=15, ge=1)
    completed: bool = False
    order_index: int = 0
