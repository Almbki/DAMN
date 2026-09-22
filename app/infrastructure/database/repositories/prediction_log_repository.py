"""PredictionLog persistence - the raw material for offline model evaluation."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import PredictionLog
from app.infrastructure.database.models.prediction_log import (
    PredictionLog as PredictionLogORM,
)
from app.infrastructure.database.repositories.base import RepositoryBase


class PredictionLogRepository(RepositoryBase):
    def create(self, entry: PredictionLog) -> PredictionLog:
        orm = PredictionLogORM(
            user_id=entry.user_id,
            plan_id=entry.plan_id,
            task_id=entry.task_id,
            model_name=entry.model_name,
            model_version=entry.model_version,
            prediction_type=entry.prediction_type,
            feature_hash=entry.feature_hash,
            predicted=entry.predicted,
            source=entry.source,
            created_at=entry.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return PredictionLog.model_validate(orm)

    def create_many(self, entries: list[PredictionLog]) -> list[PredictionLog]:
        return [self.create(entry) for entry in entries]

    def list_by_user(
        self, user_id: int, *, prediction_type: str | None = None, limit: int = 500
    ) -> list[PredictionLog]:
        stmt = select(PredictionLogORM).where(PredictionLogORM.user_id == user_id)
        if prediction_type is not None:
            stmt = stmt.where(PredictionLogORM.prediction_type == prediction_type)
        stmt = stmt.order_by(PredictionLogORM.id.desc()).limit(limit)
        return [PredictionLog.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_plan(self, plan_id: int) -> list[PredictionLog]:
        stmt = (
            select(PredictionLogORM)
            .where(PredictionLogORM.plan_id == plan_id)
            .order_by(PredictionLogORM.id)
        )
        return [PredictionLog.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_all(self, limit: int = 10000) -> list[PredictionLog]:
        """Every prediction row (reporting / offline evaluation)."""
        stmt = select(PredictionLogORM).order_by(PredictionLogORM.id.desc()).limit(limit)
        return [PredictionLog.model_validate(orm) for orm in self._session.scalars(stmt).all()]


__all__ = ["PredictionLogRepository"]
