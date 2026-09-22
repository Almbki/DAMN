"""UserState persistence (one runtime state row per user)."""

from __future__ import annotations

from sqlalchemy import select

from app.infrastructure.database.models.user_state import UserStateModel
from app.infrastructure.database.repositories.base import RepositoryBase


class UserStateRepository(RepositoryBase):
    def get_by_user_id(self, user_id: int) -> UserStateModel | None:
        return self._session.scalars(
            select(UserStateModel).where(UserStateModel.user_id == user_id).limit(1)
        ).first()

    def create(self, user_id: int, **fields: object) -> UserStateModel:
        """Create and flush a new state row, returning it with its id."""
        orm = UserStateModel(user_id=user_id, **fields)
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return orm

    def save(self, state: UserStateModel) -> UserStateModel:
        """Add or re-attach a state row and flush pending changes."""
        self._session.add(state)
        self._session.flush()
        self._session.refresh(state)
        return state