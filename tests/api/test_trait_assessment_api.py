"""Level 1 CAT assessment API tests: start/answer/resume/finish/persistence."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import get_trait_assessment_service
from app.application.services.trait_assessment_service import TraitAssessmentService
from app.core.config import get_settings
from app.infrastructure.database import SessionLocal
from app.main import app
from app.user_models.level1.runtime import Level1Runtime
from app.user_models.runtime import UserModelRuntime


def _start(client: TestClient, headers: dict) -> dict:
    response = client.post(
        "/api/v1/users/me/trait-assessment/start", headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def _answer(
    client: TestClient,
    headers: dict,
    assessment_id: str,
    item_id: str,
    value: int = 3,
) -> dict:
    response = client.post(
        f"/api/v1/users/me/trait-assessment/{assessment_id}/answer",
        json={"item_id": item_id, "response": value},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _finish(client: TestClient, headers: dict) -> dict:
    body = _start(client, headers)
    assessment_id = body["assessment_id"]
    for _ in range(80):
        if body["status"] == "completed":
            return body
        item = body["next_item"]
        assert item is not None
        body = _answer(client, headers, assessment_id, item["item_id"], 3)
    raise AssertionError("assessment did not finish within 80 answers")


def test_start_returns_a_real_item_and_progress(client: TestClient, auth_headers: dict) -> None:
    body = _start(client, auth_headers)
    assert body["status"] == "in_progress"
    assert body["next_item"]["item_id"].startswith("IPIP_")
    assert body["next_item"]["text"]
    assert body["next_item"]["domain"] in {"N", "E", "O", "A", "C"}
    assert body["progress"]["answered"] == 0
    assert body["progress"]["remaining_min"] > 0
    assert body["progress"]["total_domains"] == 5
    # Technical model values are not part of the assessment contract.
    assert "theta" not in body["next_item"]
    assert "se" not in body["progress"]


def test_restart_is_idempotent_and_resumes(client: TestClient, auth_headers: dict) -> None:
    first = _start(client, auth_headers)
    again = _start(client, auth_headers)
    assert again["assessment_id"] == first["assessment_id"]
    assert again["next_item"]["item_id"] == first["next_item"]["item_id"]


def test_answer_advances_and_resume_returns_the_same_item(
    client: TestClient, auth_headers: dict
) -> None:
    body = _start(client, auth_headers)
    assessment_id = body["assessment_id"]
    first_item = body["next_item"]["item_id"]

    after = _answer(client, auth_headers, assessment_id, first_item, 3)
    assert after["progress"]["answered"] == 1

    resumed = client.get(
        f"/api/v1/users/me/trait-assessment/{assessment_id}", headers=auth_headers
    )
    assert resumed.status_code == 200
    resumed_body = resumed.json()
    if resumed_body["status"] == "in_progress":
        assert resumed_body["next_item"]["item_id"] == after["next_item"]["item_id"]
    assert resumed_body["assessment_id"] == assessment_id


def test_invalid_response_and_unknown_item_are_422(
    client: TestClient, auth_headers: dict
) -> None:
    body = _start(client, auth_headers)
    assessment_id = body["assessment_id"]

    too_high = client.post(
        f"/api/v1/users/me/trait-assessment/{assessment_id}/answer",
        json={"item_id": body["next_item"]["item_id"], "response": 6},
        headers=auth_headers,
    )
    assert too_high.status_code == 422

    unknown = client.post(
        f"/api/v1/users/me/trait-assessment/{assessment_id}/answer",
        json={"item_id": "NOT_AN_ITEM", "response": 3},
        headers=auth_headers,
    )
    assert unknown.status_code == 422
    assert unknown.json()["code"] == "invalid_model_input"


def test_stale_item_is_409(client: TestClient, auth_headers: dict) -> None:
    body = _start(client, auth_headers)
    assessment_id = body["assessment_id"]
    first_item = body["next_item"]["item_id"]
    _answer(client, auth_headers, assessment_id, first_item, 3)

    if body["progress"]["remaining_max"] <= 1:
        return
    stale = client.post(
        f"/api/v1/users/me/trait-assessment/{assessment_id}/answer",
        json={"item_id": first_item, "response": 3},
        headers=auth_headers,
    )
    assert stale.status_code == 409


def test_cross_user_access_is_404(client: TestClient, auth_headers: dict) -> None:
    body = _start(client, auth_headers)

    email = "assessment-other@example.com"
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert registered.status_code == 201, registered.text
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        f"/api/v1/users/me/trait-assessment/{body['assessment_id']}",
        headers=other_headers,
    )
    assert response.status_code == 404


def test_finish_persists_the_trait_profile_and_is_idempotent(
    client: TestClient, auth_headers: dict
) -> None:
    completed = _finish(client, auth_headers)

    assert completed["status"] == "completed"
    assert completed["next_item"] is None
    profile = completed["trait_profile"]
    assert profile["model"] == "trait_v1"
    assert set(profile["domains"]) == {"N", "E", "O", "A", "C"}
    for domain in profile["domains"].values():
        assert domain["se"] > 0
        assert domain["items_answered"] >= 4

    # The real profile is written to users.trait_profile and exposed by /me/profile.
    me_profile = client.get("/api/v1/users/me/profile", headers=auth_headers)
    assert me_profile.status_code == 200, me_profile.text
    body = me_profile.json()
    assert body["trait"]["model_version"] == "trait_v1"
    assert body["trait"]["domains"].keys() == {"N", "E", "O", "A", "C"}

    # Starting again returns the completed assessment, not a new session.
    again = _start(client, auth_headers)
    assert again["assessment_id"] == completed["assessment_id"]
    assert again["status"] == "completed"

    answer_after = client.post(
        f"/api/v1/users/me/trait-assessment/{completed['assessment_id']}/answer",
        json={
            "item_id": "IPIP_001",
            "response": 3,
        },
        headers=auth_headers,
    )
    assert answer_after.status_code == 409


def test_restart_abandons_the_active_session(client: TestClient, auth_headers: dict) -> None:
    first = _start(client, auth_headers)
    _answer(client, auth_headers, first["assessment_id"], first["next_item"]["item_id"], 3)

    restarted = client.post(
        "/api/v1/users/me/trait-assessment/start?restart=true", headers=auth_headers
    )
    assert restarted.status_code == 200, restarted.text
    body = restarted.json()
    assert body["assessment_id"] != first["assessment_id"]
    assert body["status"] == "in_progress"

    old = client.get(
        f"/api/v1/users/me/trait-assessment/{first['assessment_id']}",
        headers=auth_headers,
    )
    assert old.status_code == 200
    assert old.json()["status"] == "abandoned"


def test_reassessment_cooldown_is_backend_authoritative(
    client: TestClient, auth_headers: dict
) -> None:
    completed = _finish(client, auth_headers)

    eligibility = client.get(
        "/api/v1/users/me/trait-assessment/reassessment-eligibility",
        headers=auth_headers,
    )
    assert eligibility.status_code == 200, eligibility.text
    body = eligibility.json()
    assert body["eligible"] is False
    assert body["cooldown_days"] >= 1
    assert body["next_eligible_at"]

    blocked = client.post(
        "/api/v1/users/me/trait-assessment/start?restart=true", headers=auth_headers
    )
    assert blocked.status_code == 409

    settings = get_settings()
    previous = settings.trait_reassessment_cooldown_days
    settings.trait_reassessment_cooldown_days = 0
    try:
        restarted = client.post(
            "/api/v1/users/me/trait-assessment/start?restart=true", headers=auth_headers
        )
    finally:
        settings.trait_reassessment_cooldown_days = previous
    assert restarted.status_code == 200, restarted.text
    assert restarted.json()["assessment_id"] != completed["assessment_id"]
    assert restarted.json()["status"] == "in_progress"


def test_unavailable_level1_returns_503(client: TestClient, auth_headers: dict, tmp_path) -> None:
    runtime = UserModelRuntime(level1=Level1Runtime(root=tmp_path))

    def factory():
        return TraitAssessmentService(SessionLocal(), runtime=runtime)

    app.dependency_overrides[get_trait_assessment_service] = factory
    try:
        response = client.post(
            "/api/v1/users/me/trait-assessment/start", headers=auth_headers
        )
    finally:
        app.dependency_overrides.pop(get_trait_assessment_service, None)
    assert response.status_code == 503
    assert response.json()["code"] == "model_unavailable"
