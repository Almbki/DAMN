"""API tests for the adaptive profile endpoints (环节 1 / 环节 3)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi.testclient import TestClient

from app.domain.profile import MBTI_TEMPLATES

_API = "/api/v1"


def _register_with_profile(client: TestClient, **profile) -> dict:
    """Register a fresh user with profile fields and return auth headers."""
    email = f"profile_{uuid.uuid4().hex[:10]}@example.com"
    payload = {"email": email, "password": "password123", "display_name": "Profiler"}
    payload.update(profile)
    register = client.post(f"{_API}/auth/register", json=payload)
    assert register.status_code == 201, register.text
    login = client.post(f"{_API}/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_with_mbti_creates_profile(client: TestClient) -> None:
    headers = _register_with_profile(client, mbti_type="intp")

    response = client.get(f"{_API}/users/me/profile", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["profile"]["mbti_type"] == "INTP"
    assert body["profile"]["mbti_dims"] is None
    assert body["state"]["update_count"] == 0
    assert body["state"]["duration_factor"] == MBTI_TEMPLATES["INTP"]["duration_factor"]
    assert body["state"]["degraded"] is True


def test_patch_mbti_dims_reinitialises_state(client: TestClient) -> None:
    headers = _register_with_profile(client, mbti_type="INTP")

    response = client.patch(
        f"{_API}/users/me", json={"mbti_dims": {"ie": 0.2}}, headers=headers
    )
    assert response.status_code == 200, response.text

    body = client.get(f"{_API}/users/me/profile", headers=headers).json()
    assert body["profile"]["mbti_type"] == "INTP"
    assert body["profile"]["mbti_dims"] == {"ie": 0.2}
    # Profile change re-initialises the dynamic state.
    assert body["state"]["update_count"] == 0
    assert body["state"]["degraded"] is True


def test_profile_missing_returns_404(client: TestClient, auth_headers: dict) -> None:
    response = client.get(f"{_API}/users/me/profile", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_feedback_increments_state_update_count(client: TestClient) -> None:
    headers = _register_with_profile(client, mbti_type="INTP")

    generated = client.post(
        f"{_API}/plans/generate",
        json={
            "goals": [{"title": "复习高数", "estimated_minutes": 120, "priority": 3}],
            "plan_title": "Profile Feedback Plan",
        },
        headers=headers,
    )
    assert generated.status_code == 202, generated.text
    plan_id = generated.json()["plan_id"]
    assert plan_id is not None

    feedback = client.post(
        f"{_API}/plans/{plan_id}/feedback",
        json={
            "date": date.today().isoformat(),
            "completion_rate": 0.9,
            "stress_level": 4,
            "energy_level": 7,
        },
        headers=headers,
    )
    assert feedback.status_code == 201, feedback.text

    body = client.get(f"{_API}/users/me/profile", headers=headers).json()
    assert body["state"]["update_count"] >= 1


def test_task_completion_increments_state_update_count(client: TestClient) -> None:
    headers = _register_with_profile(client, mbti_type="INTP")

    generated = client.post(
        f"{_API}/plans/generate",
        json={
            "goals": [{"title": "算法刷题", "estimated_minutes": 90, "priority": 2}],
            "plan_title": "Execution Profile Plan",
        },
        headers=headers,
    )
    assert generated.status_code == 202, generated.text
    body = generated.json()
    plan_id = body["plan_id"]
    task_id = body["plan"]["tasks"][0]["id"]

    patched = client.patch(
        f"{_API}/plans/{plan_id}/tasks/{task_id}",
        json={"completed": True, "actual_duration": 75},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text

    profile = client.get(f"{_API}/users/me/profile", headers=headers).json()
    assert profile["state"]["update_count"] >= 1


def test_me_patch_without_profile_fields_leaves_profile_absent(client: TestClient) -> None:
    headers = _register_with_profile(client)

    response = client.patch(
        f"{_API}/users/me", json={"display_name": "Renamed"}, headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["display_name"] == "Renamed"

    assert client.get(f"{_API}/users/me/profile", headers=headers).status_code == 404
