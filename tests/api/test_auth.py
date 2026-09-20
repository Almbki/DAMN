"""API tests for auth + users."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_docs_available(client: TestClient) -> None:
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_register_login_and_me(client: TestClient) -> None:
    email = f"api_{uuid.uuid4().hex[:10]}@example.com"
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Api Tester"},
    )
    assert register.status_code == 201, register.text
    assert register.json()["email"] == email

    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_duplicate_email_rejected(client: TestClient, registered_user: dict) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": registered_user["email"], "password": "password123"},
    )
    assert response.status_code == 409


def test_login_wrong_password(client: TestClient, registered_user: dict) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/api/v1/users/me").status_code == 401
