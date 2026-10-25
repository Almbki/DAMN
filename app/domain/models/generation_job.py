"""GenerationJobRecord domain entity - durable plan-generation job state.

The application-level ``GenerationJob`` DTO is the live, in-memory record used
by the worker/SSE machinery. This entity is the persistence snapshot: it keeps
the job status, result, error and the serialized agent events so a status poll
or SSE replay still works after a process restart.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow


class GenerationJobRecord(DomainModel):
    """One persisted generation job (preview / decompose / generate / replan)."""

    job_id: str
    user_id: int
    kind: str = "preview"
    #: pending | running | completed | failed
    status: str = "pending"
    plan_id: int | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    #: Serialized ``AgentEvent`` dicts, in emission order.
    events: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


__all__ = ["GenerationJobRecord"]
