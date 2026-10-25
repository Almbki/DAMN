"""EvidenceItem persistence (reflection evidence for Level 2)."""

from __future__ import annotations

from sqlalchemy import delete, select

from app.domain.models import EvidenceItem
from app.infrastructure.database.models.evidence_item import EvidenceItem as EvidenceItemORM
from app.infrastructure.database.repositories.base import RepositoryBase


class EvidenceItemRepository(RepositoryBase):
    def create_many(self, items: list[EvidenceItem]) -> list[EvidenceItem]:
        orms = [
            EvidenceItemORM(
                user_id=item.user_id,
                feedback_id=item.feedback_id,
                task_id=item.task_id,
                reflection_field=item.reflection_field,
                evidence_type=item.evidence_type,
                direction=item.direction,
                strength=item.strength,
                period=item.period,
                cause_category=item.cause_category,
                voluntary=item.voluntary,
                evidence_text=item.evidence_text,
                extractor=item.extractor,
                extractor_version=item.extractor_version,
                status=item.status,
                created_at=item.created_at,
            )
            for item in items
        ]
        self._session.add_all(orms)
        self._session.flush()
        for orm in orms:
            self._session.refresh(orm)
        return [EvidenceItem.model_validate(orm) for orm in orms]

    def delete_by_feedback(self, feedback_id: int) -> int:
        """Delete the rows extracted from one feedback (refresh replaces them)."""
        result = self._session.execute(
            delete(EvidenceItemORM).where(EvidenceItemORM.feedback_id == feedback_id)
        )
        return int(result.rowcount or 0)

    def list_by_feedback(self, feedback_id: int) -> list[EvidenceItem]:
        stmt = (
            select(EvidenceItemORM)
            .where(EvidenceItemORM.feedback_id == feedback_id)
            .order_by(EvidenceItemORM.id)
        )
        return [EvidenceItem.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_user(self, user_id: int, *, limit: int = 500) -> list[EvidenceItem]:
        stmt = (
            select(EvidenceItemORM)
            .where(EvidenceItemORM.user_id == user_id)
            .order_by(EvidenceItemORM.created_at.desc(), EvidenceItemORM.id.desc())
            .limit(limit)
        )
        return [EvidenceItem.model_validate(orm) for orm in self._session.scalars(stmt).all()]


__all__ = ["EvidenceItemRepository"]
