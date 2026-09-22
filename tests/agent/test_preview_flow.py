"""Pre-feedback acceptance tests: preview -> confirm (TEST1), adjust (TEST2/7)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.ml.base import AdjustmentRoute
from tests.agent.conftest import override_plan_service, preview_of


def test_preview_then_confirm_creates_plan_v1(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    """TEST 1: preview pauses, confirm persists v1."""
    override_plan_service(client, route=AdjustmentRoute.NO_CHANGE)

    body = preview_of(client, auth_headers, preview_payload)
    thread_id = body["thread_id"]
    preview = body["preview"]

    assert preview["tasks"], "preview must contain tasks"
    assert preview["can_adjust"] is True
    assert preview["adjustment_count"] == 0
    assert body["goals_persisted"] == 2
    # The preview carries ML output (completion probability from the predictor).
    assert all(task["completion_probability"] == 0.65 for task in preview["tasks"])
    # And the scheduler already proposed placement.
    assert all(task["scheduled_date"] for task in preview["tasks"])

    confirmed = client.post(
        f"/api/v1/plans/preview/{thread_id}/confirm", headers=auth_headers
    )
    assert confirmed.status_code == 201, confirmed.text
    plan = confirmed.json()["plan"]

    assert plan["version"] == 1
    assert len(plan["tasks"]) == 2
    assert plan["status"] == "active"
    # ML completion probability must survive persistence (regression guard).
    assert [task["completion_probability"] for task in plan["tasks"]] == [0.65, 0.65]


def test_preview_adjust_then_confirm(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    """TEST 2: adjust updates the preview, then confirm still yields v1."""
    override_plan_service(client)

    body = preview_of(client, auth_headers, preview_payload)
    thread_id = body["thread_id"]
    original = [task["estimated_duration"] for task in body["preview"]["tasks"]]

    adjusted = client.post(
        f"/api/v1/plans/preview/{thread_id}/adjust",
        json={"thread_id": thread_id, "feedback": "高数一天安排太多，减少一些"},
        headers=auth_headers,
    )
    assert adjusted.status_code == 200, adjusted.text
    payload = adjusted.json()
    assert payload["budget_exhausted"] is False
    assert payload["preview"]["adjustment_count"] == 1

    scaled = [task["estimated_duration"] for task in payload["preview"]["tasks"]]
    assert scaled == [max(5, round(value * 0.8)) for value in original]

    confirmed = client.post(
        f"/api/v1/plans/preview/{thread_id}/confirm", headers=auth_headers
    )
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["plan"]["version"] == 1


def test_adjustment_budget_forces_execution(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    """TEST 7: once the budget is spent the user is pushed into execution."""
    override_plan_service(client, max_preview_adjustments=1)

    body = preview_of(client, auth_headers, preview_payload)
    thread_id = body["thread_id"]

    first = client.post(
        f"/api/v1/plans/preview/{thread_id}/adjust",
        json={"thread_id": thread_id, "feedback": "少一点"},
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert first.json()["budget_exhausted"] is True  # 1 spent of 1

    # A second adjustment must be refused and the plan finalised instead.
    second = client.post(
        f"/api/v1/plans/preview/{thread_id}/adjust",
        json={"thread_id": thread_id, "feedback": "再少一点"},
        headers=auth_headers,
    )
    assert second.status_code == 200, second.text
    payload = second.json()
    assert payload["budget_exhausted"] is True
    assert payload["preview"] is None
    assert payload["final_plan"] is not None
    assert payload["final_plan"]["version"] == 1


def test_preview_requires_authentication(client: TestClient, preview_payload: dict) -> None:
    response = client.post("/api/v1/plans/preview", json=preview_payload)
    assert response.status_code == 401
