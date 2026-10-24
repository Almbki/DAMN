"""API-level smoke test for the full user-model loop.

Level 1 assessment -> plan -> execution capture -> feedback -> Level 2 refresh ->
manual replan -> Level 3 shadow audit. No UI automation is involved; the web
bundle is verified separately by `npx expo export --platform web`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from tests.support import generate_and_wait, replan_and_wait


def _complete_assessment(client: TestClient, headers: dict) -> dict:
    body = client.post(
        "/api/v1/users/me/trait-assessment/start", headers=headers
    ).json()
    for _ in range(80):
        if body["status"] == "completed":
            return body
        item = body["next_item"]
        assert item is not None
        response = client.post(
            f"/api/v1/users/me/trait-assessment/{body['assessment_id']}/answer",
            json={"item_id": item["item_id"], "response": 3},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
    raise AssertionError("assessment did not complete")


def test_user_model_closed_loop(client: TestClient, auth_headers: dict) -> None:
    today = date.today()

    # 0. New user must be in onboarding (no Level 1 yet).
    me = client.get("/api/v1/users/me", headers=auth_headers)
    assert me.status_code == 200, me.text
    assert me.json()["trait_profile"] is None

    # 1. Level 1: real CAT assessment, persisted as users.trait_profile.
    completed = _complete_assessment(client, auth_headers)
    assert completed["trait_profile"]["model"] == "trait_v1"

    profile = client.get("/api/v1/users/me/profile", headers=auth_headers)
    assert profile.status_code == 200, profile.text
    assert profile.json()["trait"] is not None
    assert profile.json()["state"] is None  # no observations yet

    # 2. Plan generation / preview-confirm path.
    generated = generate_and_wait(
        client,
        auth_headers,
        {
            "goals": [
                {
                    "title": "Smoke loop task",
                    "description": "完成一个真实执行记录",
                    "estimated_minutes": 60,
                    "start_date": today.isoformat(),
                    "deadline": (today + timedelta(days=1)).isoformat(),
                }
            ],
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
        },
    )
    plan_id = generated["plan_id"]
    task = generated["plan"]["tasks"][0]

    # 3. Task execution: start -> partial completion (real TaskExecution rows).
    started = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task['id']}",
        json={"started_at": datetime.now(UTC).isoformat()},
        headers=auth_headers,
    )
    assert started.status_code == 200, started.text

    partial = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task['id']}",
        json={
            "completed": False,
            "completion_rate": 0.5,
            "actual_duration": 30,
            "stress_after": 6,
        },
        headers=auth_headers,
    )
    assert partial.status_code == 200, partial.text

    # 4. Feedback -> Level 2 refresh.
    feedback = client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        json={
            "date": today.isoformat(),
            "completion_rate": 0.8,
            "stress_level": 5,
            "energy_level": 5,
            "free_text": "smoke test: 今天完成了一半",
        },
        headers=auth_headers,
    )
    assert feedback.status_code == 201, feedback.text

    profile = client.get("/api/v1/users/me/profile", headers=auth_headers).json()
    assert profile["state"] is not None
    assert profile["state"]["date"]
    assert profile["state"]["fatigue"]["value"] is not None
    assert profile["state"]["metadata"]["artifact_hash"]

    # 5. Manual replan -> new version, Level 3 shadow runs with Level 1+2.
    replanned = replan_and_wait(
        client, auth_headers, plan_id, {"reason": "smoke test replan"}
    )
    assert replanned["plan_id"] != plan_id
    assert replanned["new_version"] == 2

    runtime = client.get("/api/v1/users/me/model-runtime", headers=auth_headers)
    assert runtime.status_code == 200, runtime.text
    body = runtime.json()
    assert body["effective_mode"] == "shadow"
    levels = {layer["level"] for layer in body["layers"]}
    assert levels == {"level1", "level2", "level3"}
    assert body["shadow_summary"]["status"] == "ok"
    assert body["shadow_summary"]["runs"] > 0