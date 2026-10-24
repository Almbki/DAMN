"""ShadowPrediction persistence (append-only audit trail)."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models.shadow_prediction import ShadowPrediction
from app.infrastructure.database.models.shadow_prediction import (
    ShadowPrediction as ShadowPredictionORM,
)
from app.infrastructure.database.repositories.base import RepositoryBase


class ShadowPredictionRepository(RepositoryBase):
    def create(self, entry: ShadowPrediction) -> ShadowPrediction:
        orm = ShadowPredictionORM(
            user_id=entry.user_id,
            plan_id=entry.plan_id,
            task_id=entry.task_id,
            inference_timestamp=entry.inference_timestamp,
            model_level=entry.model_level,
            model_version=entry.model_version,
            artifact_hash=entry.artifact_hash,
            artifact_version=entry.artifact_version,
            feature_version=entry.feature_version,
            input_hash=entry.input_hash,
            input_summary=entry.input_summary,
            production_decision=entry.production_decision,
            shadow_prediction=entry.shadow_prediction,
            confidence=entry.confidence,
            uncertainty=entry.uncertainty,
            disagreement=entry.disagreement,
            latency_ms=entry.latency_ms,
            success=entry.success,
            failure_reason=entry.failure_reason,
            degraded=entry.degraded,
            mode=entry.mode,
            data_origin=entry.data_origin,
            created_at=entry.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return ShadowPrediction.model_validate(orm)

    def list_by_user(self, user_id: int, *, limit: int = 100) -> list[ShadowPrediction]:
        stmt = (
            select(ShadowPredictionORM)
            .where(ShadowPredictionORM.user_id == user_id)
            .order_by(ShadowPredictionORM.id.desc())
            .limit(limit)
        )
        return [
            ShadowPrediction.model_validate(orm)
            for orm in self._session.scalars(stmt).all()
        ]

    def list_by_plan(self, plan_id: int) -> list[ShadowPrediction]:
        stmt = (
            select(ShadowPredictionORM)
            .where(ShadowPredictionORM.plan_id == plan_id)
            .order_by(ShadowPredictionORM.id)
        )
        return [
            ShadowPrediction.model_validate(orm)
            for orm in self._session.scalars(stmt).all()
        ]

    def latest_for_user(self, user_id: int) -> ShadowPrediction | None:
        rows = self.list_by_user(user_id, limit=1)
        return rows[0] if rows else None


__all__ = ["ShadowPredictionRepository"]