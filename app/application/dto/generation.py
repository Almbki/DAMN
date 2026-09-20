"""Plan-generation job DTOs (used by the SSE flow)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.agent.graph import GenerationEvent


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationJob(BaseModel):
    """In-memory record of one plan generation run.

    First version runs the pipeline synchronously in ``create_job`` and stores
    the ordered events; the SSE endpoint replays them. Marked as MOCK/PENDING
    for a real background worker.
    """

    job_id: str
    user_id: int
    status: JobStatus = JobStatus.PENDING
    plan_id: int | None = None
    error: str | None = None
    events: list[GenerationEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
