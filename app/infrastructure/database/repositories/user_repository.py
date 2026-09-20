"""User persistence."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import User
from app.infrastructure.database.models.user import User as UserORM
from app.infrastructure.database.repositories.base import RepositoryBase


class UserRepository(RepositoryBase):
    def create(self, user: User) -> User:
        """Persist a new user row and return it with its generated id."""
        orm = UserORM(
            email=user.email,
            password_hash=user.password_hash,
            display_name=user.display_name,
            execution_weight=user.execution_weight,
            profile=user.profile,
            created_at=user.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return User.model_validate(orm)

    def get_by_id(self, user_id: int) -> User | None:
        orm = self._session.get(UserORM, user_id)
        return User.model_validate(orm) if orm is not None else None

    def get_by_email(self, email: str) -> User | None:
        orm = self._session.scalars(select(UserORM).where(UserORM.email == email)).first()
        return User.model_validate(orm) if orm is not None else None

    def update_fields(self, user_id: int, **fields: object) -> User | None:
        """Update arbitrary columns and return the refreshed domain model."""
        orm = self._session.get(UserORM, user_id)
        if orm is None:
            return None
        for key, value in fields.items():
            setattr(orm, key, value)
        self._session.flush()
        self._session.refresh(orm)
        return User.model_validate(orm)