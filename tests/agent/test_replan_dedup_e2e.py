"""End-to-end: partial chunk completion must survive FULL_REPLAN without duplication."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.domain.feedback.models import AdjustmentRoute, AdjustmentSeverity
from tests.agent.conftest import override_plan_service, preview_of


def test_full_replan_keeps_completed_chunk_out_of_new_version(
    client: TestClient, auth_headers: dict
) -> None:
    override_plan_service(
        client,
        route=AdjustmentRoute.FULL_REPLAN,
        severity=AdjustmentSeverity.HIGH,
    )
    start = date.today() + timedelta(days=1)
    payload = {
        "goals": [
            {
                "title": "big one-off",
                "planning_mode": "one_off",
                "deadline": start.isoformat(),
                "estimated_minutes": 120,
            }
        ],
        "start_date": start.isoformat(),
        "end_date": start.isoformat(),
        "daily_limit_minutes": 60,
    }
    preview = preview_of(client, auth_headers, payload)
    confirmed = client.post(
        f"/api/v1/plans/preview/{preview['thread_id']}/confirm",
        headers=auth_headers,
    )
    assert confirmed.status_code == 201, confirmed.text
    old_plan = confirmed.json()["plan"]
    old_plan_id = old_plan["id"]
    old_tasks = sorted(old_plan["tasks"], key=lambda task: task["chunk_index"])
    assert len(old_tasks) == 2
    assert all(task["work_unit_key"] for task in old_tasks)

    completed_chunk = old_tasks[0]
    completed = client.patch(
        f"/api/v1/plans/{old_plan_id}/tasks/{completed_chunk['id']}",
        json={"completed": True},
        headers=auth_headers,
    )
    assert completed.status_code == 200, completed.text

    feedback = client.post(
        f"/api/v1/plans/{old_plan_id}/feedback",
        json={
            "date": date.today().isoformat(),
            "completion_rate": 0.2,
            "stress_level": 9,
            "energy_level": 2,
        },
        headers=auth_headers,
    )
    assert feedback.status_code == 201, feedback.text
    body = feedback.json()
    assert body["replan_decision"] == "full_replan"
    new_plan_id = (
        (body.get("adjustment") or {}).get("new_plan_id")
        or body.get("replan_plan_id")
    )
    assert new_plan_id is not None
    assert new_plan_id != old_plan_id

    new_plan = client.get(
        f"/api/v1/plans/{new_plan_id}", headers=auth_headers
    ).json()
    new_tasks = new_plan["tasks"]

    # The completed 60-minute chunk is history, not a new todo. Only the
    # remaining 60 minutes is materialized in the new version.
    assert len(new_tasks) == 1
    assert new_tasks[0]["estimated_duration"] == 60
    assert new_tasks[0]["work_unit_key"] == completed_chunk["work_unit_key"]
    assert new_tasks[0]["id"] != completed_chunk["id"]

    # The old plan version remains immutable and keeps the completion record.
    old_again = client.get(
        f"/api/v1/plans/{old_plan_id}", headers=auth_headers
    ).json()
    assert len(old_again["tasks"]) == 2
    assert any(task["status"] == "completed" for task in old_again["tasks"])
