"""UserModel persistence (one statistical factors row per user)."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import UserModel
from app.infrastructure.database.models.user_model import UserModel as UserModelORM
from app.infrastructure.database.repositories.base import RepositoryBase


class UserModelRepository(RepositoryBase):
    def get_by_user(self, user_id: int) -> UserModel | None:
        orm = self._session.scalars(
            select(UserModelORM).where(UserModelORM.user_id == user_id).limit(1)
        ).first()
        return UserModel.model_validate(orm) if orm is not None else None

    def upsert(self, model: UserModel) -> UserModel:
        """Insert or update the single factors row for the user."""
        existing = self._session.scalars(
            select(UserModelORM).where(UserModelORM.user_id == model.user_id).limit(1)
        ).first()

        if existing is None:
            orm = UserModelORM(
                user_id=model.user_id,
                model_version=model.model_version,
                duration_factors=model.duration_factors,
                completion_probability=model.completion_probability,
                stress_response=model.stress_response,
                preferred_time_slots=model.preferred_time_slots,
                sample_size=model.sample_size,
                updated_at=model.updated_at,
            )
            self._session.add(orm)
            self._session.flush()
            self._session.refresh(orm)
            return UserModel.model_validate(orm)

        existing.model_version = model.model_version
        existing.duration_factors = model.duration_factors
        existing.completion_probability = model.completion_probability
        existing.stress_response = model.stress_response
        existing.preferred_time_slots = model.preferred_time_slots
        existing.sample_size = model.sample_size
        existing.updated_at = model.updated_at
        self._session.flush()
        return UserModel.model_validate(existing)