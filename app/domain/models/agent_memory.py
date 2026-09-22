"""AgentMemory domain entity - persisted semantic / episodic / procedural memory.

The first version derives memory from existing rows on every run. Persisting it
lets the system keep information that cannot be re-derived (explicit user
preferences, consolidated rules of thumb) and lets the agent read it back
cheaply.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow


class AgentMemory(DomainModel):
    id: int | None = None
    user_id: int
    #: semantic | episodic | procedural (kept as str so the domain layer does
    #: not depend on the agent-layer enum).
    kind: str
    key: str
    value: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    #: Provenance: users.profile | task_executions | feedbacks | explicit_user | derived
    source: str = "derived"
    updated_at: datetime = Field(default_factory=utcnow)
