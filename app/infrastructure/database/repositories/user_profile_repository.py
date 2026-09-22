"""UserProfile persistence (one profile row per user)."""

from __future__ import annotations

from sqlalchemy import select

from app.infrastructure.database.models.user_profile import UserProfileModel
from app.infrastructure.database.repositories.base import RepositoryBase


class UserProfileRepository(RepositoryBase):
    def get_by_user_id(self, user_id: int) -> UserProfileModel | None:
        return self._session.scalars(
            select(UserProfileModel).where(UserProfileModel.user_id == user_id).limit(1)
        ).first()

    def create(self, user_id: int, **fields: object) -> UserProfileModel:
        """Create and flush a new profile row, returning it with its id."""
        orm = UserProfileModel(user_id=user_id, **fields)
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return orm

    def save(self, profile: UserProfileModel) -> UserProfileModel:
        """Add or re-attach a profile and flush pending changes."""
        self._session.add(profile)
        self._session.flush()
        self._session.refresh(profile)
        return profile