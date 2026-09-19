"""Auth service: registration, authentication, JWT issuance."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.models import User
from app.infrastructure.database.repositories import UserRepository


class AuthService:
    """Owns user credentials. Transaction boundaries are managed by callers
    (see ``app.api.deps``) or by :meth:`register`'s explicit flush."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)

    def register(
        self,
        email: str,
        password: str,
        display_name: str | None = None,
        execution_weight: float = 0.5,
        profile: dict | None = None,
    ) -> User:
        if self._users.get_by_email(email) is not None:
            raise ConflictError("email already registered")
        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            execution_weight=execution_weight,
            profile=profile or {},
        )
        created = self._users.create(user)
        self._session.commit()
        return created

    def authenticate(self, email: str, password: str) -> User:
        user = self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("invalid email or password")
        return user

    def create_token(self, user: User) -> str:
        if user.id is None:  # pragma: no cover - defensive
            raise AuthenticationError("user has no id")
        return create_access_token(user.id)

    def get_user(self, user_id: int) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("user not found")
        return user

    def update_user(
        self,
        user_id: int,
        *,
        display_name: str | None = None,
        execution_weight: float | None = None,
        profile: dict | None = None,
    ) -> User:
        user = self.get_user(user_id)
        updates: dict[str, object] = {}
        if display_name is not None:
            updates["display_name"] = display_name
        if execution_weight is not None:
            updates["execution_weight"] = execution_weight
        if profile is not None:
            updates["profile"] = profile
        if updates:
            updated = self._users.update_fields(user_id, **updates)
            self._session.commit()
            if updated is not None:
                return updated
        return user
