"""API tests for the plan lifecycle."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from tests.support import generate_and_wait, replan_and_wait

_GOALS = [
    {
        "title": "复习高数极限",
        "description": "看课\n做例题\n做练习\n总结",
        "subject": "math",
        "estimated_minutes": 120,
        "priority": 3,
    },
    {
        "title": "算法刷题",
        "description": "做两题\n复盘",
        "subject": "algorithm",
        "estimated_minutes": 90,
        "priority": 2,
    },
]


def _generate(client: TestClient, headers: dict, **overrides) -> dict:
    payload = {"goals": _GOALS, "plan_title": "Test Plan"}
    payload.update(overrides)
    return generate_and_wait(client, headers, payload)


def test_generate_plan_returns_job_and_plan(client: TestClient, auth_headers: dict) -> None:
    body = _generate(client, auth_headers)
    assert body["job_id"]
    assert body["plan_id"] is not None
    assert body["status"] == "completed"
    assert body["events_url"].endswith(f"/plans/generation/{body['job_id']}/events")
    assert body["plan"]["tasks"]


def test_sse_generation_events(client: TestClient, auth_headers: dict) -> None:
    body = _generate(client, auth_headers)
    response = client.get(body["events_url"], headers=auth_headers)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: goal_analysis" in response.text
    assert "event: completed" in response.text


def test_list_and_get_plan(client: TestClient, auth_headers: dict) -> None:
    body = _generate(client, auth_headers)
    plan_id = body["plan_id"]

    listing = client.get("/api/v1/plans", headers=auth_headers)
    assert listing.status_code == 200
    assert any(item["id"] == plan_id for item in listing.json())

    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["id"] == plan_id
    assert payload["version"] == 1
    assert len(payload["tasks"]) >= 1
    assert payload["goals"]


def test_task_patch_records_completion(client: TestClient, auth_headers: dict) -> None:
    body = _generate(client, auth_headers)
    plan_id = body["plan_id"]
    task_id = body["plan"]["tasks"][0]["id"]

    response = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}",
        json={"completed": True, "actual_duration": 75, "difficulty_feedback": 4},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"

    # The completion must also be recorded as an execution row.
    insights = client.get(f"/api/v1/plans/{plan_id}/insights", headers=auth_headers)
    assert insights.status_code == 200, insights.text
    assert insights.json()["total_actual_minutes"] == 75


def test_task_patch_edits_and_reschedules(client: TestClient, auth_headers: dict) -> None:
    body = _generate(client, auth_headers)
    plan_id = body["plan_id"]
    task_id = body["plan"]["tasks"][0]["id"]
    day = date.today()
    payload = {
        "title": "编辑后的任务",
        "estimated_duration": 45,
        "priority": 4,
        "scheduled_date": day.isoformat(),
        "start_time": "09:30:00",
        "end_time": "10:15:00",
    }

    response = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text

    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers)
    assert detail.status_code == 200, detail.text
    task = next(item for item in detail.json()["tasks"] if item["id"] == task_id)
    assert task["title"] == payload["title"]
    assert task["estimated_duration"] == payload["estimated_duration"]
    assert task["priority"] == payload["priority"]
    assert task["scheduled_date"] == payload["scheduled_date"]
    assert task["start_time"] == payload["start_time"]
    assert task["end_time"] == payload["end_time"]


def test_feedback_submission_and_history(client: TestClient, auth_headers: dict) -> None:
    body = _generate(client, auth_headers)
    plan_id = body["plan_id"]
    payload = {
        "date": date.today().isoformat(),
        "completion_rate": 0.8,
        "stress_level": 5,
        "energy_level": 6,
        "delay_reason": "too many tasks",
    }
    response = client.post(
        f"/api/v1/plans/{plan_id}/feedback", json=payload, headers=auth_headers
    )
    assert response.status_code == 201, response.text
    assert response.json()["feedback"]["completion_rate"] == 0.8

    history = client.get(f"/api/v1/plans/{plan_id}/feedback", headers=auth_headers)
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_replan_eligibility_and_replan(client: TestClient, auth_headers: dict) -> None:
    body = _generate(client, auth_headers)
    plan_id = body["plan_id"]

    eligibility = client.get(
        f"/api/v1/plans/{plan_id}/replan/eligibility", headers=auth_headers
    )
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible"] is True

    replanned = replan_and_wait(
        client, auth_headers, plan_id, {"reason": "manual test"}
    )
    assert replanned["new_version"] == 2


def test_insights(client: TestClient, auth_headers: dict) -> None:
    body = _generate(client, auth_headers)
    plan_id = body["plan_id"]
    response = client.get(f"/api/v1/plans/{plan_id}/insights", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_tasks"] >= 1
    assert "cognitive_load_breakdown" in payload


def test_plan_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/plans").status_code == 401
