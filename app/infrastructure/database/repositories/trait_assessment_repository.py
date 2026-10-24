"""TraitAssessment persistence (flush-only; services own transactions)."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models.trait_assessment import TraitAssessment
from app.infrastructure.database.models.trait_assessment import (
    TraitAssessmentModel,
)
from app.infrastructure.database.repositories.base import RepositoryBase


class TraitAssessmentRepository(RepositoryBase):
    def create(self, entry: TraitAssessment) -> TraitAssessment:
        orm = TraitAssessmentModel(
            id=entry.id,
            user_id=entry.user_id,
            status=entry.status,
            responses=entry.responses,
            rr_index=entry.rr_index,
            unavailable=entry.unavailable,
            current_item_id=entry.current_item_id,
            model_version=entry.model_version,
            calibration_version=entry.calibration_version,
            artifact_hash=entry.artifact_hash,
            feature_version=entry.feature_version,
            trait_profile=entry.trait_profile,
            data_origin=entry.data_origin,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            completed_at=entry.completed_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return TraitAssessment.model_validate(orm)

    def get_by_id(self, assessment_id: str) -> TraitAssessment | None:
        orm = self._session.get(TraitAssessmentModel, assessment_id)
        return TraitAssessment.model_validate(orm) if orm is not None else None

    def get_active_for_user(self, user_id: int) -> TraitAssessment | None:
        stmt = (
            select(TraitAssessmentModel)
            .where(
                TraitAssessmentModel.user_id == user_id,
                TraitAssessmentModel.status == "in_progress",
            )
            .order_by(TraitAssessmentModel.updated_at.desc())
            .limit(1)
        )
        orm = self._session.scalars(stmt).first()
        return TraitAssessment.model_validate(orm) if orm is not None else None

    def get_latest_for_user(self, user_id: int) -> TraitAssessment | None:
        stmt = (
            select(TraitAssessmentModel)
            .where(TraitAssessmentModel.user_id == user_id)
            .order_by(TraitAssessmentModel.created_at.desc())
            .limit(1)
        )
        orm = self._session.scalars(stmt).first()
        return TraitAssessment.model_validate(orm) if orm is not None else None

    def get_latest_completed_for_user(self, user_id: int) -> TraitAssessment | None:
        stmt = (
            select(TraitAssessmentModel)
            .where(
                TraitAssessmentModel.user_id == user_id,
                TraitAssessmentModel.status == "completed",
            )
            .order_by(TraitAssessmentModel.completed_at.desc())
            .limit(1)
        )
        orm = self._session.scalars(stmt).first()
        return TraitAssessment.model_validate(orm) if orm is not None else None

    def update_fields(self, assessment_id: str, **fields: object) -> TraitAssessment | None:
        orm = self._session.get(TraitAssessmentModel, assessment_id)
        if orm is None:
            return None
        for key, value in fields.items():
            setattr(orm, key, value)
        self._session.flush()
        self._session.refresh(orm)
        return TraitAssessment.model_validate(orm)


__all__ = ["TraitAssessmentRepository"]