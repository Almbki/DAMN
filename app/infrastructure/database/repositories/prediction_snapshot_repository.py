"""PredictionSnapshot persistence (frozen Level-3 inputs)."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import PredictionSnapshot
from app.infrastructure.database.models.prediction_snapshot import (
    PredictionSnapshot as PredictionSnapshotORM,
)
from app.infrastructure.database.repositories.base import RepositoryBase


class PredictionSnapshotRepository(RepositoryBase):
    def create(self, snapshot: PredictionSnapshot) -> PredictionSnapshot:
        orm = PredictionSnapshotORM(
            user_id=snapshot.user_id,
            task_id=snapshot.task_id,
            plan_id=snapshot.plan_id,
            prediction_timestamp=snapshot.prediction_timestamp,
            trait=snapshot.trait,
            state=snapshot.state,
            task=snapshot.task,
            context=snapshot.context,
            history=snapshot.history,
            feature_snapshot=snapshot.feature_snapshot,
            input_hash=snapshot.input_hash,
            model_version=snapshot.model_version,
            config_version=snapshot.config_version,
            artifact_hash=snapshot.artifact_hash,
            mode=snapshot.mode,
            data_origin=snapshot.data_origin,
            created_at=snapshot.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return PredictionSnapshot.model_validate(orm)

    def get_by_id(self, snapshot_id: int) -> PredictionSnapshot | None:
        orm = self._session.get(PredictionSnapshotORM, snapshot_id)
        return PredictionSnapshot.model_validate(orm) if orm is not None else None

    def get_latest_for_task(self, task_id: int) -> PredictionSnapshot | None:
        stmt = (
            select(PredictionSnapshotORM)
            .where(PredictionSnapshotORM.task_id == task_id)
            .order_by(
                PredictionSnapshotORM.prediction_timestamp.desc(),
                PredictionSnapshotORM.id.desc(),
            )
            .limit(1)
        )
        orm = self._session.scalars(stmt).first()
        return PredictionSnapshot.model_validate(orm) if orm is not None else None

    def list_by_task(self, task_id: int, *, limit: int = 50) -> list[PredictionSnapshot]:
        stmt = (
            select(PredictionSnapshotORM)
            .where(PredictionSnapshotORM.task_id == task_id)
            .order_by(
                PredictionSnapshotORM.prediction_timestamp.desc(),
                PredictionSnapshotORM.id.desc(),
            )
            .limit(limit)
        )
        return [
            PredictionSnapshot.model_validate(orm)
            for orm in self._session.scalars(stmt).all()
        ]

    def list_by_user(self, user_id: int, *, limit: int = 500) -> list[PredictionSnapshot]:
        stmt = (
            select(PredictionSnapshotORM)
            .where(PredictionSnapshotORM.user_id == user_id)
            .order_by(PredictionSnapshotORM.prediction_timestamp.desc())
            .limit(limit)
        )
        return [PredictionSnapshot.model_validate(orm) for orm in self._session.scalars(stmt).all()]


__all__ = ["PredictionSnapshotRepository"]
