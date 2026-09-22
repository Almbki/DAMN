"""Memory service: consolidate derived memory into ``agent_memories``.

Reading history is cheap but recomputing it every run is not, and some
information (explicit preferences, consolidated rules of thumb) cannot be
re-derived from raw rows. This service is the write side of the memory loop;
:class:`app.application.context.RepoContextBuilder` is the read side.

Memory is derived from the portrait state (`user_states`) and the raw history -
the retired `user_models` aggregate is no longer involved.
"""

from __future__ import annotations

import logging

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
    UserRepository,
    UserStateRepository,
)

#: Episodic memory is append-only; keep the most recent N entries per user.
EPISODIC_KEEP = 50

#: ``agent_memories.summary`` is VARCHAR(500). Derived summaries (e.g. the raw
#: user profile field list) can exceed it and abort the transaction.
_SUMMARY_MAX_LEN = 500

logger = logging.getLogger(__name__)


def _clip_summary(value: str | None) -> str | None:
    """Fit a derived summary into ``agent_memories.summary`` (VARCHAR(500))."""
    if value is None:
        return None
    text = str(value).strip()
    if len(text) <= _SUMMARY_MAX_LEN:
        return text
    logger.warning(
        "memory summary too long (%d chars, max %d); truncating: %.80s",
        len(text),
        _SUMMARY_MAX_LEN,
        text,
    )
    return text[:_SUMMARY_MAX_LEN]


class MemoryService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._memories = AgentMemoryRepository(session)
        self._users = UserRepository(session)
        self._states = UserStateRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._feedback = FeedbackRepository(session)

    def refresh(self, user_id: int) -> list[AgentMemory]:
        """Re-derive memory from history and upsert it (consolidation).

        Semantic and procedural entries are *upserted* (one row per key, so the
        latest consolidated view wins); episodic entries accumulate and are
        pruned to :data:`EPISODIC_KEEP`.
        """
        user = self._users.get_by_id(user_id)
        state = self._states.get_by_user(user_id)
        executions = self._executions.list_by_user(user_id)
        feedbacks = self._feedback.list_by_user(user_id)
        profile = (user.profile if user else None) or {}
        mbti = (user.mbti_type if user else None) or profile.get("mbti")

        items = [
            *build_semantic_memory(user, state, mbti=mbti),
            *build_episodic_memory(executions, feedbacks),
            *derive_procedural_memory(state, executions, feedbacks),
        ]

        saved = self._memories.upsert_many(
            [
                AgentMemory(
                    user_id=user_id,
                    kind=item.kind.value,
                    key=item.key,
                    value=item.value,
                    summary=_clip_summary(item.summary),
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
