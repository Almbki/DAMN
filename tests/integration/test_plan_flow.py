"""Integration test: the full feedback loop across layers.

goals -> generate (langgraph + rules + scheduler) -> execute -> feedback ->
auto-replan (new version) -> cooldown -> insights.
"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient


def test_full_adaptive_loop(client: TestClient, auth_headers: dict) -> None:
    # 1. Generate v1.
    generated = client.post(
        "/api/v1/plans/generate",
        json={
            "goals": [
                {
                    "title": "高数冲刺",
                    "description": "看课\n做例题\n做练习",
                    "subject": "math",
                    "estimated_minutes": 150,
                    "priority": 4,
                }
            ],
            "plan_title": "Integration Plan",
            "daily_limit_minutes": 200,
        },
        headers=auth_headers,
    )
    assert generated.status_code == 202, generated.text
    plan_id = generated.json()["plan_id"]
    assert plan_id is not None

    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    tasks = detail["tasks"]
    assert tasks, "expected generated tasks"
    task_id = tasks[0]["id"]

    # 2. Execute one task (records TaskExecution - the ML data asset).
    patched = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}",
        json={"completed": True, "actual_duration": 90, "stress_before": 3, "stress_after": 6},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text

    # 3. Low completion feedback triggers an automatic replan.
    feedback = client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        json={
            "date": date.today().isoformat(),
            "completion_rate": 0.4,
            "stress_level": 8,
            "energy_level": 3,
            "free_text": "not enough time",
        },
        headers=auth_headers,
    )
    assert feedback.status_code == 201, feedback.text
    body = feedback.json()
    assert body["replan_triggered"] is True
    assert body["replan_plan_id"] is not None
    new_plan_id = body["replan_plan_id"]
    assert new_plan_id != plan_id

    # 4. Old plan is superseded; the new version links back to it.
    old_plan = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    new_plan = client.get(f"/api/v1/plans/{new_plan_id}", headers=auth_headers).json()
    assert old_plan["status"] == "superseded"
    assert new_plan["status"] == "active"
    assert new_plan["version"] == 2
    assert new_plan["parent_plan_id"] == plan_id

    # 5. Cooldown now blocks another replan.
    eligibility = client.get(
        f"/api/v1/plans/{new_plan_id}/replan/eligibility", headers=auth_headers
    )
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible"] is False

    blocked = client.post(
        f"/api/v1/plans/{new_plan_id}/replan",
        json={"reason": "too soon"},
        headers=auth_headers,
    )
    assert blocked.status_code == 409

    # 6. Insights remain available on the new version.
    insights = client.get(f"/api/v1/plans/{new_plan_id}/insights", headers=auth_headers)
    assert insights.status_code == 200
