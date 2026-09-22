"""TEST 8 / TEST 9: manual replan and the cooldown that guards it."""

from __future__ import annotations

import time
from datetime import date, timedelta

from fastapi.testclient import TestClient


def _create_plan(client: TestClient, headers: dict) -> int:
    response = client.post(
        "/api/v1/plans/preview",
        json={
            "goals": [
                {
                    "title": "复习高数极限",
                    "description": "看课\n做例题",
                    "subject": "math",
                    "estimated_minutes": 120,
                    "priority": 3,
                }
            ],
            "plan_title": "Cooldown Plan",
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=13)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    deadline = time.time() + 120
    while True:
        status = client.get(f"/api/v1/plans/generation/{job_id}", headers=headers)
        assert status.status_code == 200, status.text
        body = status.json()
        if body["status"] in {"completed", "failed"}:
            break
        assert time.time() < deadline, f"preview job still {body['status']}"
        time.sleep(0.05)
    assert body["status"] == "completed", body
    thread_id = body["result"]["thread_id"]
    confirmed = client.post(
        f"/api/v1/plans/preview/{thread_id}/confirm", headers=headers
    )
    assert confirmed.status_code == 201, confirmed.text
    return confirmed.json()["plan"]["id"]


def test_manual_replan_succeeds_when_eligible(client: TestClient, auth_headers: dict) -> None:
    """TEST 8: cooldown clear -> replan creates a new version."""
    plan_id = _create_plan(client, auth_headers)

    eligibility = client.get(
        f"/api/v1/plans/{plan_id}/replan/eligibility", headers=auth_headers
    )
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible"] is True

    response = client.post(
        f"/api/v1/plans/{plan_id}/replan",
        json={"reason": "manual replan test"},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["old_version"] == 1
    assert body["new_version"] == 2
    assert body["plan_id"] != plan_id

    new_plan = client.get(f"/api/v1/plans/{body['plan_id']}", headers=auth_headers).json()
    assert new_plan["version"] == 2
    assert new_plan["parent_plan_id"] == plan_id
    assert new_plan["tasks"]


def test_manual_replan_blocked_by_cooldown(client: TestClient, auth_headers: dict) -> None:
    """TEST 9: second replan is refused with a reason and a next-eligible time."""
    plan_id = _create_plan(client, auth_headers)
    first = client.post(
        f"/api/v1/plans/{plan_id}/replan",
        json={"reason": "first replan"},
        headers=auth_headers,
    )
    assert first.status_code == 201, first.text
    new_plan_id = first.json()["plan_id"]

    eligibility = client.get(
        f"/api/v1/plans/{new_plan_id}/replan/eligibility", headers=auth_headers
    )
    assert eligibility.status_code == 200
    payload = eligibility.json()
    assert payload["eligible"] is False
    assert payload["next_eligible_at"] is not None
    assert payload["cooldown_hours"] > 0
    assert payload["reason"]

    blocked = client.post(
        f"/api/v1/plans/{new_plan_id}/replan",
        json={"reason": "too soon"},
        headers=auth_headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "replan_not_eligible"
    assert blocked.json()["detail"]["eligible"] is False
