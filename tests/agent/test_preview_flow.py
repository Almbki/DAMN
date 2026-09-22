"""Pre-feedback acceptance tests: preview -> confirm (TEST1), adjust (TEST2/7)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.ml.base import AdjustmentRoute
from tests.agent.conftest import override_plan_service, preview_of, run_job


def _adjust(client: TestClient, headers: dict, thread_id: str, feedback: str) -> dict:
    """Submit an async adjust job and return its result payload."""
    response = client.post(
        f"/api/v1/plans/preview/{thread_id}/adjust",
        json={"feedback": feedback},
        headers=headers,
    )
    assert response.status_code == 202, response.text
    body = run_job(client, headers, response.json()["job_id"])
    assert body["status"] == "completed", body
    return body["result"]


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

    payload = _adjust(client, auth_headers, thread_id, "高数一天安排太多，减少一些")
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

    first = _adjust(client, auth_headers, thread_id, "少一点")
    assert first["budget_exhausted"] is True  # 1 spent of 1

    # A second adjustment must be refused and the plan finalised instead.
    payload = _adjust(client, auth_headers, thread_id, "再少一点")
    assert payload["budget_exhausted"] is True
    assert payload["preview"] is None
    assert payload["final_plan"] is not None
    assert payload["final_plan"]["version"] == 1


def test_preview_requires_authentication(client: TestClient, preview_payload: dict) -> None:
    response = client.post("/api/v1/plans/preview", json=preview_payload)
    assert response.status_code == 401


def test_preview_job_streams_events_and_result(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    """The preview is a real async job: it returns 202 immediately and streams
    node stages over SSE, ending with a `completed` frame that carries the preview."""
    import json

    override_plan_service(client)

    accepted = client.post("/api/v1/plans/preview", json=preview_payload, headers=auth_headers)
    assert accepted.status_code == 202, accepted.text
    job_id = accepted.json()["job_id"]

    frames: list[tuple[str, str]] = []
    with client.stream(
        "GET", f"/api/v1/plans/generation/{job_id}/events", headers=auth_headers
    ) as response:
        assert response.status_code == 200, response.status_code
        name = ""
        for line in response.iter_lines():
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                frames.append((name, line.split(":", 1)[1].strip()))

    assert frames, "no SSE frames"
    assert frames[-1][0] == "completed", frames[-1]
    assert any(name == "goal_analysis" for name, _ in frames)
    result = json.loads(frames[-1][1])
    assert result["status"] == "completed"
    assert result["result"]["thread_id"]
