"""Pre-feedback acceptance tests: preview -> confirm (TEST1), adjust (TEST2/7)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.domain.feedback.models import AdjustmentRoute
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
    # Production is deterministic: no completion probability is fabricated.
    assert all(task["completion_probability"] is None for task in preview["tasks"])
    assert all(
        task["predicted_duration"] == task["estimated_duration"]
        for task in preview["tasks"]
    )
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
    # No production completion probability exists; it must stay null.
    assert [task["completion_probability"] for task in plan["tasks"]] == [None, None]
    assert all(
        task["prediction_source"] == "deterministic:workload_estimate"
        for task in plan["tasks"]
    )


def test_long_term_goal_persists_daily_occurrences(
    client: TestClient, auth_headers: dict
) -> None:
    """A dated long-term goal becomes one task per day (series), not one giant task."""
    override_plan_service(client)
    start = date.today()
    end = start + timedelta(days=6)
    payload = {
        "goals": [
            {
                "title": "高等数学复习",
                "goal_type": "long_term",
                "start_date": start.isoformat(),
                "deadline": end.isoformat(),
                "daily_target_minutes": 60,
                "estimated_minutes": 420,
                "subject": "math",
                "priority": 3,
            }
        ],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }

    body = preview_of(client, auth_headers, payload)
    tasks = body["preview"]["tasks"]
    expected_days = [(start + timedelta(days=offset)).isoformat() for offset in range(7)]

    assert len(tasks) == 7
    assert {task["series_id"] for task in tasks} == {"goal-1-long_term"}
    assert {task["task_kind"] for task in tasks} == {"long_term"}
    assert {task["is_flexible"] for task in tasks} == {False}
    assert [task["occurrence_date"] for task in tasks] == expected_days
    assert [task["scheduled_date"] for task in tasks] == expected_days
    assert all(task["standards"] for task in tasks)

    confirmed = client.post(
        f"/api/v1/plans/preview/{body['thread_id']}/confirm", headers=auth_headers
    )
    assert confirmed.status_code == 201, confirmed.text
    persisted = confirmed.json()["plan"]["tasks"]

    assert [task["occurrence_date"] for task in persisted] == expected_days
    assert {task["series_id"] for task in persisted} == {"goal-1-long_term"}
    assert {task["task_kind"] for task in persisted} == {"long_term"}
    assert [task["scheduled_date"] for task in persisted] == expected_days


def test_one_off_goal_stays_one_task(
    client: TestClient, auth_headers: dict
) -> None:
    override_plan_service(client)
    payload = {
        "goals": [
            {
                "title": "去超市买酱油",
                "goal_type": "short_term",
                "estimated_minutes": 30,
            }
        ],
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=6)).isoformat(),
    }

    body = preview_of(client, auth_headers, payload)
    tasks = body["preview"]["tasks"]

    assert len(tasks) == 1
    assert tasks[0]["task_kind"] == "one_off"
    assert tasks[0]["series_id"] is None
    assert tasks[0]["occurrence_date"] is None


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
