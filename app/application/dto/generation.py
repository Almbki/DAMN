"""Plan-generation job DTOs (used by the SSE flow)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentEvent(BaseModel):
    """One agent event as emitted by :class:`app.agent.graph.RunEvents`.

    ``event`` is the event name (``node.started``, ``node.completed``,
    ``tool.completed``, ``waiting_user_confirmation``, ``agent.completed`` ...).
    ``node`` is set on node events, which is what the SSE stream uses as the
    ``event:`` name so the documented stage contract is preserved.
    """

    event: str
    node: str | None = None
    stage: str | None = None
    status: str = "completed"
    summary: str = ""
    payload: dict = Field(default_factory=dict)
    progress: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_dict(cls, raw: dict) -> AgentEvent:
        node = raw.get("node")
        return cls(
            event=str(raw.get("event", "event")),
            node=node,
            stage=raw.get("stage") or node,
            status=str(raw.get("status", "completed")),
            summary=str(raw.get("summary", "")),
            payload={
                k: v
                for k, v in raw.items()
                if k not in {"event", "node", "stage", "status", "summary"}
            },
        )


class GenerationJob(BaseModel):
    """In-memory record of one plan generation run.

    The first version runs the pipeline synchronously in ``create_job`` and
    stores the ordered events; the SSE endpoint replays them.
    """

    job_id: str
    user_id: int
    status: JobStatus = JobStatus.PENDING
    plan_id: int | None = None
    error: str | None = None
    events: list[AgentEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = ["AgentEvent", "GenerationJob", "JobStatus"]
