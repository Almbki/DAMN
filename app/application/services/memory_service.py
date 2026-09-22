"""Memory service: consolidate derived memory into ``agent_memories``.

Reading history is cheap but recomputing it every run is not, and some
information (explicit preferences, consolidated rules of thumb) cannot be
re-derived from raw rows. This service is the write side of the memory loop;
:class:`app.application.context.RepoContextBuilder` is the read side.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agent.context import MemoryKind
from app.agent.memory import (
    build_episodic_memory,
    build_semantic_memory,
    derive_procedural_memory,
)
from app.domain.models import AgentMemory
from app.infrastructure.database.repositories import (
    AgentMemoryRepository,
    FeedbackRepository,
    TaskExecutionRepository,
    UserModelRepository,
    UserRepository,
)

#: Episodic memory is append-only; keep the most recent N entries per user.
EPISODIC_KEEP = 50


class MemoryService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._memories = AgentMemoryRepository(session)
        self._users = UserRepository(session)
        self._models = UserModelRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._feedback = FeedbackRepository(session)

    def refresh(self, user_id: int) -> list[AgentMemory]:
        """Re-derive memory from history and upsert it (consolidation).

        Semantic and procedural entries are *upserted* (one row per key, so the
        latest consolidated view wins); episodic entries accumulate and are
        pruned to :data:`EPISODIC_KEEP`.
        """
        user = self._users.get_by_id(user_id)
        model = self._models.get_by_user(user_id)
        executions = self._executions.list_by_user(user_id)
        feedbacks = self._feedback.list_by_user(user_id)
        profile = (user.profile if user else None) or {}

        items = [
            *build_semantic_memory(user, model, mbti=profile.get("mbti")),
            *build_episodic_memory(executions, feedbacks),
            *derive_procedural_memory(model, executions, feedbacks),
        ]

        saved = self._memories.upsert_many(
            [
                AgentMemory(
                    user_id=user_id,
                    kind=item.kind.value,
                    key=item.key,
                    value=item.value,
                    summary=item.summary,
                    confidence=item.confidence,
                    source=item.source,
                )
                for item in items
            ]
        )
        self._memories.prune_by_kind(user_id, MemoryKind.EPISODIC.value, EPISODIC_KEEP)
        self._session.commit()
        return saved

    def get_memories(self, user_id: int, *, kind: str | None = None) -> list[AgentMemory]:
        return self._memories.list_by_user(user_id, kind=kind)

    def forget(self, user_id: int) -> int:
        """Delete all persisted memory for a user (privacy / reset)."""
        removed = self._memories.delete_by_user(user_id)
        self._session.commit()
        return removed


__all__ = ["EPISODIC_KEEP", "MemoryService"]
