"""Regression guards for the hardening pass: the 422 error envelope and input limits."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def test_validation_errors_use_the_error_envelope(client: TestClient) -> None:
    """FastAPI's default 422 body is {"detail": [...]}; the frontend expects
    {code, message, detail}, so an explicit handler must wrap it."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "short"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["message"]
    assert "errors" in body["detail"]


def test_overlong_display_name_is_rejected_before_the_db(client: TestClient) -> None:
    """`users.display_name` is VARCHAR(255); an over-long value must 422, not 500."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"x{uuid.uuid4().hex[:8]}@example.com",
            "password": "Passw0rd!123",
            "display_name": "a" * 300,
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
