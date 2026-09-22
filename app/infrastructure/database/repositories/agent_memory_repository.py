"""AgentMemory persistence (structured semantic / episodic / procedural memory)."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import AgentMemory
from app.infrastructure.database.models.agent_memory import AgentMemory as AgentMemoryORM
from app.infrastructure.database.repositories.base import RepositoryBase


class AgentMemoryRepository(RepositoryBase):
    def upsert(self, memory: AgentMemory) -> AgentMemory:
        """Insert or update by (user_id, kind, key) - memory must stay consolidated."""
        orm = self._session.scalars(
            select(AgentMemoryORM).where(
                AgentMemoryORM.user_id == memory.user_id,
                AgentMemoryORM.kind == memory.kind,
                AgentMemoryORM.key == memory.key,
            )
        ).first()
        if orm is None:
            orm = AgentMemoryORM(
                user_id=memory.user_id,
                kind=memory.kind,
                key=memory.key,
                value=memory.value,
                summary=memory.summary,
                confidence=memory.confidence,
                source=memory.source,
                updated_at=memory.updated_at,
            )
            self._session.add(orm)
        else:
            orm.value = memory.value
            orm.summary = memory.summary
            orm.confidence = memory.confidence
            orm.source = memory.source
            orm.updated_at = memory.updated_at
        self._session.flush()
        self._session.refresh(orm)
        return AgentMemory.model_validate(orm)

    def upsert_many(self, memories: list[AgentMemory]) -> list[AgentMemory]:
        return [self.upsert(memory) for memory in memories]

    def list_by_user(self, user_id: int, *, kind: str | None = None) -> list[AgentMemory]:
        stmt = select(AgentMemoryORM).where(AgentMemoryORM.user_id == user_id)
        if kind is not None:
            stmt = stmt.where(AgentMemoryORM.kind == kind)
        stmt = stmt.order_by(AgentMemoryORM.kind, AgentMemoryORM.key)
        return [AgentMemory.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def delete_by_user(self, user_id: int) -> int:
        rows = self._session.scalars(
            select(AgentMemoryORM).where(AgentMemoryORM.user_id == user_id)
        ).all()
        for orm in rows:
            self._session.delete(orm)
        self._session.flush()
        return len(rows)

    def prune_by_kind(self, user_id: int, kind: str, keep: int) -> int:
        """Keep only the ``keep`` most recently updated rows of one kind.

        Episodic memory is append-only, so without pruning it grows forever.
        """
        rows = self._session.scalars(
            select(AgentMemoryORM)
            .where(AgentMemoryORM.user_id == user_id, AgentMemoryORM.kind == kind)
            .order_by(AgentMemoryORM.updated_at.desc(), AgentMemoryORM.id.desc())
        ).all()
        removed = 0
        for orm in rows[keep:]:
            self._session.delete(orm)
            removed += 1
        self._session.flush()
        return removed


__all__ = ["AgentMemoryRepository"]
