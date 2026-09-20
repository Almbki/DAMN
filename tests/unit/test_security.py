"""Unit tests for core security primitives."""

from __future__ import annotations

import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-password")
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_hash_is_salted() -> None:
    assert hash_password("same") != hash_password("same")


def test_verify_rejects_garbage() -> None:
    assert not verify_password("x", "not-a-valid-hash")


def test_jwt_roundtrip() -> None:
    token = create_access_token(42)
    payload = decode_access_token(token)
    assert payload.sub == "42"
    assert payload.type == "access"


def test_jwt_rejects_garbage() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("not.a.token")
