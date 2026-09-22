"""API tests for the user-portrait module (static MBTI + adaptive state)."""

from __future__ import annotations

from fastapi.testclient import TestClient

_ONE_GOAL = [
    {
        "title": "复习高数极限",
        "description": "看课\n做例题",
        "subject": "math",
        "estimated_minutes": 120,
        "priority": 3,
    }
]


def _profile(client: TestClient, headers: dict) -> dict:
    response = client.get("/api/v1/users/me/profile", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _make_plan(client: TestClient, headers: dict) -> int:
    response = client.post(
        "/api/v1/plans/generate", json={"goals": _ONE_GOAL}, headers=headers
    )
    assert response.status_code == 202, response.text
    return response.json()["plan_id"]


# ---------------------------------------------------------------------------
# read / 404
# ---------------------------------------------------------------------------
def test_profile_is_404_before_it_is_set(client: TestClient, auth_headers: dict) -> None:
    response = client.get("/api/v1/users/me/profile", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_patch_creates_the_portrait_and_seeds_the_state(
    client: TestClient, auth_headers: dict
) -> None:
    patched = client.patch(
        "/api/v1/users/me",
        json={"mbti_type": "intp", "identity": "研究生"},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["mbti_type"] == "INTP"  # normalised to upper case

    body = _profile(client, auth_headers)
    assert body["mbti_type"] == "INTP"
    assert body["identity"] == "研究生"
    assert body["update_count"] == 0
    assert body["degraded"] is True  # cold start
    assert 0.0 < body["duration_factor"] < 3.0
    assert set(body["preferred_time_slots"]) == {"high", "medium", "low", "restorative"}


def test_portrait_is_not_created_by_unrelated_profile_edits(
    client: TestClient, auth_headers: dict
) -> None:
    client.patch("/api/v1/users/me", json={"display_name": "Ann"}, headers=auth_headers)
    assert client.get("/api/v1/users/me/profile", headers=auth_headers).status_code == 404


def test_mbti_dims_blend_the_templates(client: TestClient, auth_headers: dict) -> None:
    whole = client.patch(
        "/api/v1/users/me", json={"mbti_type": "INTJ"}, headers=auth_headers
    )
    assert whole.status_code == 200
    pure = _profile(client, auth_headers)["duration_factor"]

    client.patch(
        "/api/v1/users/me",
        json={"mbti_dims": {"ie": 0.0, "jp": 0.0}},  # fully flip I->E and J->P
        headers=auth_headers,
    )
    flipped = _profile(client, auth_headers)
    assert flipped["duration_factor"] != pure
    assert flipped["mbti_dims"] == {"ie": 0.0, "jp": 0.0}


def test_unknown_dimension_key_is_rejected(client: TestClient, auth_headers: dict) -> None:
    response = client.patch(
        "/api/v1/users/me", json={"mbti_dims": {"xx": 0.5}}, headers=auth_headers
    )
    assert response.status_code == 422


def test_explicit_null_clears_a_portrait_field(
    client: TestClient, auth_headers: dict
) -> None:
    client.patch(
        "/api/v1/users/me",
        json={"mbti_type": "INTP", "identity": "研究生"},
        headers=auth_headers,
    )
    client.patch("/api/v1/users/me", json={"identity": None}, headers=auth_headers)

    body = _profile(client, auth_headers)
    assert body["identity"] is None
    assert body["mbti_type"] == "INTP"  # untouched field kept


def test_registration_can_seed_the_portrait(client: TestClient) -> None:
    email = "portrait@example.com"
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "mbti_type": "ENFP"},
    )
    assert registered.status_code == 201, registered.text
    assert registered.json()["mbti_type"] == "ENFP"

    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]
    body = _profile(client, {"Authorization": f"Bearer {token}"})
    assert body["mbti_type"] == "ENFP"
    assert body["update_count"] == 0


# ---------------------------------------------------------------------------
# closed loop: feedback / execution -> EWMA state
# ---------------------------------------------------------------------------
def test_feedback_updates_the_adaptive_state(client: TestClient, auth_headers: dict) -> None:
    client.patch("/api/v1/users/me", json={"mbti_type": "INTP"}, headers=auth_headers)
    plan_id = _make_plan(client, auth_headers)
    before = _profile(client, auth_headers)

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

    after = _profile(client, auth_headers)
    assert after["update_count"] == before["update_count"] + 1
    assert after["state_energy"] == round(0.3 * 0.4 + 0.7 * before["state_energy"], 6)
    assert after["stress_baseline"] > before["stress_baseline"]
    assert after["self_efficacy"] > before["self_efficacy"]  # completed task


def test_task_completion_moves_the_duration_factor(
    client: TestClient, auth_headers: dict
) -> None:
    client.patch("/api/v1/users/me", json={"mbti_type": "INTJ"}, headers=auth_headers)
    plan_id = _make_plan(client, auth_headers)
    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    task = detail["tasks"][0]
    before = _profile(client, auth_headers)

    # Report a large overrun: the factor must move up.
    patched = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task['id']}",
        json={"completed": True, "actual_duration": task["estimated_duration"] * 3},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text

    after = _profile(client, auth_headers)
    assert after["duration_factor"] > before["duration_factor"]
    assert after["update_count"] == before["update_count"] + 1


def test_changing_the_portrait_resets_the_state(
    client: TestClient, auth_headers: dict
) -> None:
    client.patch("/api/v1/users/me", json={"mbti_type": "INTP"}, headers=auth_headers)
    plan_id = _make_plan(client, auth_headers)
    client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        json={"date": "2026-09-20", "completion_rate": 1.0},
        headers=auth_headers,
    )
    assert _profile(client, auth_headers)["update_count"] == 1

    client.patch("/api/v1/users/me", json={"mbti_type": "ENFJ"}, headers=auth_headers)
    reset = _profile(client, auth_headers)
    assert reset["update_count"] == 0  # initial values come from the template
    assert reset["mbti_type"] == "ENFJ"


def test_portrait_drives_the_plan_predictions(client: TestClient, auth_headers: dict) -> None:
    """The state's duration_factor must reach the persisted task predictions."""
    client.patch("/api/v1/users/me", json={"mbti_type": "INTP"}, headers=auth_headers)
    state = _profile(client, auth_headers)

    plan_id = _make_plan(client, auth_headers)
    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    task = detail["tasks"][0]

    assert task["predicted_duration"] is not None
    assert task["predicted_duration"] != task["estimated_duration"]  # factor applied
    assert task["predicted_duration"] >= task["estimated_duration"] or state[
        "duration_factor"
    ] < 1.0


def test_profile_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/users/me/profile").status_code == 401
