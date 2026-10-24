"""API tests for the real three-layer user model (Level 1 trait + Level 2 state)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.support import generate_and_wait

_ONE_GOAL = [
    {
        "title": "复习高数极限",
        "description": "看课\n做例题",
        "subject": "math",
        "estimated_minutes": 120,
        "priority": 3,
    }
]


def _trait_profile(theta: float = 0.2) -> dict:
    return {
        "schema_version": "1.0",
        "model": "trait_v1",
        "instrument": "IPIP-NEO-120",
        "method": "bayesian_cat",
        "calibration": {
            "model": "samejima_grm",
            "version": "grm_v1",
            "reference_population": "Johnson_IPIP_NEO_120",
        },
        "domains": {
            domain: {
                "theta": theta,
                "se": 0.3,
                "ci95": [theta - 0.5, theta + 0.5],
                "items_answered": 8,
            }
            for domain in ("N", "E", "O", "A", "C")
        },
        "assessment": {"total_items_answered": 40, "completed": True},
    }


def _profile(client: TestClient, headers: dict) -> dict:
    response = client.get("/api/v1/users/me/profile", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _make_plan(client: TestClient, headers: dict) -> int:
    return generate_and_wait(client, headers, {"goals": _ONE_GOAL})["plan_id"]


def _set_trait(client: TestClient, headers: dict) -> None:
    response = client.patch(
        "/api/v1/users/me",
        json={"trait_profile": _trait_profile()},
        headers=headers,
    )
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# read / 404 / static portrait
# ---------------------------------------------------------------------------
def test_profile_is_404_before_it_is_set(client: TestClient, auth_headers: dict) -> None:
    response = client.get("/api/v1/users/me/profile", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_patch_creates_the_soft_portrait(client: TestClient, auth_headers: dict) -> None:
    patched = client.patch(
        "/api/v1/users/me",
        json={"mbti_type": "intp", "identity": "研究生"},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["mbti_type"] == "INTP"

    body = _profile(client, auth_headers)
    assert body["mbti_type"] == "INTP"
    assert body["identity"] == "研究生"
    # No Level 1/2 model yet: the legacy fields are neutral and nothing is claimed.
    assert body["trait"] is None
    assert body["state"] is None
    assert body["update_count"] == 0
    assert body["degraded"] is True


def test_trait_profile_is_validated_and_exposed(
    client: TestClient, auth_headers: dict
) -> None:
    _set_trait(client, auth_headers)
    body = _profile(client, auth_headers)
    assert body["trait"]["model_version"] == "trait_v1"
    assert set(body["trait"]["domains"]) == {"N", "E", "O", "A", "C"}
    assert body["trait"]["metadata"]["artifact_hash"]
    assert body["state"] is None


def test_invalid_trait_profile_is_422(client: TestClient, auth_headers: dict) -> None:
    broken = _trait_profile()
    del broken["domains"]["C"]
    response = client.patch(
        "/api/v1/users/me", json={"trait_profile": broken}, headers=auth_headers
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_model_input"


def test_portrait_is_not_created_by_unrelated_profile_edits(
    client: TestClient, auth_headers: dict
) -> None:
    client.patch("/api/v1/users/me", json={"display_name": "Ann"}, headers=auth_headers)
    assert client.get("/api/v1/users/me/profile", headers=auth_headers).status_code == 404


def test_unknown_dimension_key_is_rejected(client: TestClient, auth_headers: dict) -> None:
    response = client.patch(
        "/api/v1/users/me", json={"mbti_dims": {"xx": 0.5}}, headers=auth_headers
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Level 2 dynamic state from real observations
# ---------------------------------------------------------------------------
def test_feedback_refreshes_the_level2_state(
    client: TestClient, auth_headers: dict
) -> None:
    _set_trait(client, auth_headers)
    plan_id = _make_plan(client, auth_headers)

    response = client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        json={
            "date": "2026-09-20",
            "completion_rate": 1.0,
            "energy_level": 4,
            "stress_level": 7,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text

    body = _profile(client, auth_headers)
    assert body["state"] is not None
    assert body["state"]["model_version"] == "ddsr_v1"
    assert body["state"]["metadata"]["artifact_hash"]
    assert body["update_count"] >= 1
    # Legacy fields are projections of the Level 2 snapshot, not a second model.
    assert body["state_fatigue"] == body["state"]["fatigue"]["value"]
    assert body["state_stress"] == body["state"]["stress"]["value"]
    assert body["self_efficacy"] == body["state"]["self_efficacy"]["value"]


def test_task_completion_records_execution_without_fabricating_a_prediction(
    client: TestClient, auth_headers: dict
) -> None:
    _set_trait(client, auth_headers)
    plan_id = _make_plan(client, auth_headers)
    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    task = detail["tasks"][0]

    # Production has no trained completion model: the estimate is the task's own.
    assert task["predicted_duration"] == task["estimated_duration"]
    assert task["completion_probability"] is None
    assert task["prediction_source"] == "deterministic:workload_estimate"

    patched = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task['id']}",
        json={"completed": True, "actual_duration": task["estimated_duration"] + 20},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text

    body = _profile(client, auth_headers)
    assert body["state"] is not None
    assert body["state"]["date"]


def test_partial_execution_fields_are_not_dropped(
    client: TestClient, auth_headers: dict
) -> None:
    _set_trait(client, auth_headers)
    plan_id = _make_plan(client, auth_headers)
    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    task = detail["tasks"][0]

    patched = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task['id']}",
        json={
            "completed": False,
            "completion_rate": 0.5,
            "actual_duration": 30,
            "stress_after": 6,
        },
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text

    from app.domain.models import TaskExecution
    from app.infrastructure.database import SessionLocal
    from app.infrastructure.database.repositories import TaskExecutionRepository

    session = SessionLocal()
    try:
        executions = TaskExecutionRepository(session).list_by_task(task["id"])
    finally:
        session.close()

    assert len(executions) == 1
    execution = executions[0]
    assert execution.completed is False
    assert execution.completion_rate == 0.5
    assert execution.actual_duration == 30
    assert execution.stress_after == 6
    assert isinstance(execution, TaskExecution)


def test_changing_the_soft_portrait_does_not_reset_level2(
    client: TestClient, auth_headers: dict
) -> None:
    _set_trait(client, auth_headers)
    plan_id = _make_plan(client, auth_headers)
    client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        json={"date": "2026-09-20", "completion_rate": 1.0},
        headers=auth_headers,
    )
    before = _profile(client, auth_headers)

    client.patch("/api/v1/users/me", json={"mbti_type": "ENFJ"}, headers=auth_headers)
    after = _profile(client, auth_headers)

    assert after["mbti_type"] == "ENFJ"
    assert after["update_count"] == before["update_count"]
    assert after["state"] is not None


def test_model_runtime_endpoint_reports_modes_and_shadow_summary(
    client: TestClient, auth_headers: dict
) -> None:
    _set_trait(client, auth_headers)
    response = client.get("/api/v1/users/me/model-runtime", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["effective_mode"] == "shadow"
    levels = {layer["level"]: layer for layer in body["layers"]}
    assert set(levels) == {"level1", "level2", "level3"}
    assert all(layer["artifact_hash"] for layer in levels.values())
    assert body["shadow_summary"]["status"] in {"ok", "no_runtime_data"}


def test_profile_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/users/me/profile").status_code == 401