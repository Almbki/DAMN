"""Synthetic scenario import/reset tests (feature-flagged, current-user only)."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import (
    FeedbackRepository,
    ShadowPredictionRepository,
    TaskExecutionRepository,
)
from tests.support import generate_and_wait


@pytest.fixture()
def synthetic_enabled():
    settings = get_settings()
    previous = settings.enable_synthetic_import
    settings.enable_synthetic_import = True
    try:
        yield
    finally:
        settings.enable_synthetic_import = previous


def _import(client: TestClient, headers: dict, name: str = "stable_executor"):
    return client.post(
        "/api/v1/dev/scenarios/import",
        json={"scenario_name": name},
        headers=headers,
    )


def test_feature_disabled_returns_404(client: TestClient, auth_headers: dict) -> None:
    settings = get_settings()
    previous = settings.enable_synthetic_import
    settings.enable_synthetic_import = False
    try:
        response = _import(client, auth_headers)
    finally:
        settings.enable_synthetic_import = previous
    assert response.status_code == 404


def test_unauthenticated_returns_401(client: TestClient, synthetic_enabled) -> None:
    response = client.post(
        "/api/v1/dev/scenarios/import", json={"scenario_name": "stable_executor"}
    )
    assert response.status_code == 401


def test_import_uses_real_level2_and_level3(
    client: TestClient, auth_headers: dict, synthetic_enabled
) -> None:
    response = _import(client, auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scenario"] == "stable_executor"
    assert body["days_imported"] == 5
    assert body["tasks_imported"] > 0
    assert body["executions_imported"] == body["tasks_imported"]
    assert body["feedback_imported"] == 5
    assert body["level1_status"] == "ready"
    assert body["level2_status"] == "ready"
    assert body["level2_observed_on"] is not None
    assert body["shadow_runs_after"] > body["shadow_runs_before"]

    user_id = client.get("/api/v1/users/me", headers=auth_headers).json()["id"]
    session = SessionLocal()
    try:
        executions = TaskExecutionRepository(session).list_by_user(user_id)
        shadow = ShadowPredictionRepository(session).list_by_user(user_id)
    finally:
        session.close()
    assert executions
    assert all(item.data_origin == "synthetic" for item in executions)
    # Missing interruptions are None; explicit zero is a real observation.
    assert any(item.interruption_count is None for item in executions)
    assert any(item.interruption_count == 0 for item in executions)
    assert shadow
    assert all(item.data_origin == "synthetic" for item in shadow)

    profile = client.get("/api/v1/users/me/profile", headers=auth_headers)
    assert profile.status_code == 200, profile.text
    assert profile.json()["trait"] is not None
    assert profile.json()["state"] is not None

    status = client.get("/api/v1/dev/scenarios/status", headers=auth_headers)
    assert status.status_code == 200
    assert status.json()["synthetic_present"] is True


def test_reset_removes_only_synthetic_and_allows_reimport(
    client: TestClient, auth_headers: dict, synthetic_enabled
) -> None:
    assert _import(client, auth_headers).status_code == 200
    reset = client.post("/api/v1/dev/scenarios/reset", headers=auth_headers)
    assert reset.status_code == 200, reset.text
    body = reset.json()
    assert body["deleted"]["plans"] >= 1
    assert body["deleted"]["task_executions"] >= 1
    assert body["level1_status"] == "unavailable"

    status = client.get("/api/v1/dev/scenarios/status", headers=auth_headers)
    assert status.json()["synthetic_present"] is False
    assert client.get("/api/v1/users/me/profile", headers=auth_headers).status_code == 404

    again = _import(client, auth_headers)
    assert again.status_code == 200, again.text
    assert again.json()["level2_status"] == "ready"


def test_reset_does_not_delete_real_data(
    client: TestClient, auth_headers: dict, synthetic_enabled
) -> None:
    generated = generate_and_wait(
        client,
        auth_headers,
        {
            "goals": [{"title": "Real task", "estimated_minutes": 30}],
            "start_date": date.today().isoformat(),
        },
    )
    plan_id = generated["plan_id"]
    feedback = client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        json={"date": date.today().isoformat(), "completion_rate": 0.9},
        headers=auth_headers,
    )
    assert feedback.status_code == 201, feedback.text

    assert _import(client, auth_headers).status_code == 200
    assert client.post("/api/v1/dev/scenarios/reset", headers=auth_headers).status_code == 200

    assert client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).status_code == 200
    session = SessionLocal()
    try:
        rows = FeedbackRepository(session).list_by_plan(plan_id)
    finally:
        session.close()
    assert len(rows) == 1
    assert rows[0].data_origin == "real"


def test_request_cannot_specify_a_target_user(
    client: TestClient, auth_headers: dict, synthetic_enabled
) -> None:
    response = client.post(
        "/api/v1/dev/scenarios/import",
        json={"scenario_name": "stable_executor", "user_id": 999},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_invalid_scenario_is_rejected_and_rolls_back(
    client: TestClient, auth_headers: dict, synthetic_enabled
) -> None:
    response = client.post(
        "/api/v1/dev/scenarios/import",
        json={
            "scenario": {
                "scenario_version": "1.0",
                "name": "no-level1",
                "days": [
                    {
                        "date": "2026-09-01",
                        "tasks": [
                            {"title": "x", "estimated_duration_minutes": 30}
                        ],
                    }
                ],
            }
        },
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text

    status = client.get("/api/v1/dev/scenarios/status", headers=auth_headers)
    assert status.json()["synthetic_present"] is False


def test_invalid_execution_values_are_422(
    client: TestClient, auth_headers: dict, synthetic_enabled
) -> None:
    response = client.post(
        "/api/v1/dev/scenarios/import",
        json={
            "scenario": {
                "scenario_version": "1.0",
                "name": "bad-values",
                "level1": {
                    "trait_profile": {
                        "model": "trait_v1",
                        "domains": {},
                    }
                },
                "days": [
                    {
                        "date": "2026-09-01",
                        "tasks": [
                            {
                                "title": "bad",
                                "estimated_duration_minutes": 30,
                                "completion_rate": 2.0,
                            }
                        ],
                    }
                ],
            }
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_repeat_import_is_allowed_and_remains_synthetic(
    client: TestClient, auth_headers: dict, synthetic_enabled
) -> None:
    assert _import(client, auth_headers).status_code == 200
    assert _import(client, auth_headers).status_code == 200

    status = client.get("/api/v1/dev/scenarios/status", headers=auth_headers)
    assert status.status_code == 200
    assert status.json()["synthetic_present"] is True

    user_id = client.get("/api/v1/users/me", headers=auth_headers).json()["id"]
    session = SessionLocal()
    try:
        shadow = ShadowPredictionRepository(session).list_by_user(user_id)
    finally:
        session.close()
    assert shadow
    assert all(item.data_origin == "synthetic" for item in shadow)


def test_reset_restores_an_imported_real_trait(
    client: TestClient, auth_headers: dict, synthetic_enabled
) -> None:
    trait_profile = {
        "schema_version": "1.0",
        "model": "trait_v1",
        "instrument": "IPIP-NEO-120",
        "method": "bayesian_cat",
        "calibration": {"model": "samejima_grm", "version": "grm_v1"},
        "domains": {
            domain: {
                "theta": 0.1,
                "se": 0.3,
                "ci95": [-0.5, 0.7],
                "items_answered": 8,
            }
            for domain in ("N", "E", "O", "A", "C")
        },
        "assessment": {"total_items_answered": 40, "completed": True},
    }
    patched = client.patch(
        "/api/v1/users/me",
        json={"trait_profile": trait_profile},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text

    assert _import(client, auth_headers).status_code == 200
    reset = client.post("/api/v1/dev/scenarios/reset", headers=auth_headers)
    assert reset.status_code == 200, reset.text

    profile = client.get("/api/v1/users/me/profile", headers=auth_headers)
    assert profile.status_code == 200, profile.text
    assert profile.json()["trait"] is not None


def test_reset_does_not_affect_another_user(
    client: TestClient, auth_headers: dict, synthetic_enabled
) -> None:
    assert _import(client, auth_headers).status_code == 200

    email = "synthetic-neighbour@example.com"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    ).status_code == 201
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {token}"}
    assert _import(client, other_headers, "recovery").status_code == 200

    assert client.post("/api/v1/dev/scenarios/reset", headers=auth_headers).status_code == 200
    other_status = client.get("/api/v1/dev/scenarios/status", headers=other_headers)
    assert other_status.json()["synthetic_present"] is True