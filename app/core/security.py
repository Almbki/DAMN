"""Security primitives: password hashing + JWT encoding/decoding.

Deliberately framework free so the domain/application layers can use it
without importing FastAPI or SQLAlchemy.

Password hashing uses the standard library PBKDF2-HMAC-SHA256 (no native
build dependency). It is intentionally isolated behind ``hash_password`` /
``verify_password`` so it can be swapped for Argon2/bcrypt later without
touching callers.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings

_ALGORITHM = "pbkdf2_sha256"
_SALT_BYTES = 16


class TokenPayload(BaseModel):
    """Decoded JWT payload for this application."""

    sub: str
    exp: int
    iat: int
    type: str = "access"


class InvalidTokenError(Exception):
    """Raised when a token is malformed, expired or has a bad signature."""


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(password: str, settings: Settings | None = None) -> str:
    """Hash a plaintext password, returning ``pbkdf2_sha256$iter$salt$digest``."""
    settings = settings or get_settings()
    if not password:
        raise ValueError("password must not be empty")

    salt = secrets.token_bytes(_SALT_BYTES)
    iterations = settings.password_hash_iterations
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)

    return "$".join(
        [
            _ALGORITHM,
            str(iterations),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time verification of a plaintext password against a hash."""
    if not password or not password_hash:
        return False

    try:
        algorithm, iterations_str, salt_b64, digest_b64 = password_hash.split("$")
        if algorithm != _ALGORITHM:
            return False
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def create_access_token(
    subject: str | int,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
    settings: Settings | None = None,
    token_type: str = "access",
) -> str:
    """Create a signed JWT access token for ``subject`` (usually user id)."""
    settings = settings or get_settings()
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> TokenPayload:
    """Decode and validate a JWT, raising :class:`InvalidTokenError` on failure."""
    settings = settings or get_settings()
    try:
        raw = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        payload = TokenPayload.model_validate(raw)
    except (jwt.PyJWTError, ValidationError) as exc:  # pragma: no cover - defensive
        raise InvalidTokenError(str(exc)) from exc
    if payload.type != "access":
        raise InvalidTokenError("unexpected token type")
    return payload
