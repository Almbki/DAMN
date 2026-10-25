"""PredictionOutcome persistence (observed result of one prediction)."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import PredictionOutcome
from app.infrastructure.database.models.prediction_outcome import (
    PredictionOutcome as PredictionOutcomeORM,
)
from app.infrastructure.database.repositories.base import RepositoryBase


class PredictionOutcomeRepository(RepositoryBase):
    def create(self, outcome: PredictionOutcome) -> PredictionOutcome:
        orm = PredictionOutcomeORM(
            snapshot_id=outcome.snapshot_id,
            task_id=outcome.task_id,
            completed=outcome.completed,
            completion_ratio=outcome.completion_ratio,
            actual_duration_minutes=outcome.actual_duration_minutes,
            outcome_timestamp=outcome.outcome_timestamp,
            notes=outcome.notes,
            source=outcome.source,
            created_at=outcome.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return PredictionOutcome.model_validate(orm)

    def get_by_snapshot(self, snapshot_id: int) -> PredictionOutcome | None:
        stmt = select(PredictionOutcomeORM).where(
            PredictionOutcomeORM.snapshot_id == snapshot_id
        )
        orm = self._session.scalars(stmt).first()
        return PredictionOutcome.model_validate(orm) if orm is not None else None

    def list_by_task(self, task_id: int) -> list[PredictionOutcome]:
        stmt = (
            select(PredictionOutcomeORM)
            .where(PredictionOutcomeORM.task_id == task_id)
            .order_by(PredictionOutcomeORM.id)
        )
        return [PredictionOutcome.model_validate(orm) for orm in self._session.scalars(stmt).all()]


__all__ = ["PredictionOutcomeRepository"]
