"""Phase 5 feedback loop: close-day, estimate corrections, auto duration, stats."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import TaskExecutionRepository
from tests.support import generate_and_wait


def _plan_with_tasks(
    client: TestClient, headers: dict, minutes: int = 30
) -> dict:
    return generate_and_wait(
        client,
        headers,
        {
            "goals": [{"title": "Phase 5 task", "estimated_minutes": minutes}],
            "start_date": date.today().isoformat(),
        },
    )


def _patch_task(
    client: TestClient, headers: dict, plan_id: int, task_id: int, payload: dict
) -> dict:
    response = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _submit_feedback(
    client: TestClient, headers: dict, plan_id: int, **extra: object
) -> dict:
    payload: dict = {"date": date.today().isoformat(), "completion_rate": 1.0}
    payload.update(extra)
    response = client.post(
        f"/api/v1/plans/{plan_id}/feedback", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def _latest_execution(task_id: int):
    session = SessionLocal()
    try:
        executions = TaskExecutionRepository(session).list_by_task(task_id)
        return executions[-1] if executions else None
    finally:
        session.close()


def test_feedback_reminder_defaults_to_2200_enabled(
    client: TestClient, auth_headers: dict
) -> None:
    response = client.get("/api/v1/users/me/preferences", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["feedback_time"] == "22:00"
    assert body["feedback_enabled"] is True


def test_close_day_stamps_day_closed_at(client: TestClient, auth_headers: dict) -> None:
    generated = _plan_with_tasks(client, auth_headers)
    plan_id = generated["plan_id"]

    body = _submit_feedback(client, auth_headers, plan_id, close_day=True)
    assert body["feedback"]["day_closed_at"] is not None

    listed = client.get(
        f"/api/v1/plans/{plan_id}/feedback", headers=auth_headers
    ).json()
    assert listed[0]["day_closed_at"] == body["feedback"]["day_closed_at"]


def test_close_day_defaults_to_open(client: TestClient, auth_headers: dict) -> None:
    generated = _plan_with_tasks(client, auth_headers)
    plan_id = generated["plan_id"]

    body = _submit_feedback(client, auth_headers, plan_id)
    assert body["feedback"]["day_closed_at"] is None


def test_task_estimates_patch_the_latest_execution(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _plan_with_tasks(client, auth_headers)
    plan_id = generated["plan_id"]
    task_id = generated["plan"]["tasks"][0]["id"]
    _patch_task(client, auth_headers, plan_id, task_id, {"completed": True})

    body = _submit_feedback(
        client,
        auth_headers,
        plan_id,
        task_estimates=[
            {"task_id": task_id, "accuracy": "over", "actual_minutes": 25},
            # Unknown / foreign task ids are skipped (best effort, no 4xx).
            {"task_id": 999_999, "accuracy": "under", "actual_minutes": 5},
        ],
    )
    assert body["feedback"]["id"] > 0

    execution = _latest_execution(task_id)
    assert execution is not None
    assert execution.estimate_feedback == "over"
    assert execution.actual_duration == 25


def test_task_estimates_skip_tasks_without_execution(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _plan_with_tasks(client, auth_headers)
    plan_id = generated["plan_id"]
    task_id = generated["plan"]["tasks"][0]["id"]

    body = _submit_feedback(
        client,
        auth_headers,
        plan_id,
        task_estimates=[{"task_id": task_id, "accuracy": "ok"}],
    )
    assert body["feedback"]["id"] > 0
    assert _latest_execution(task_id) is None


def test_started_and_finished_auto_compute_actual_duration(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _plan_with_tasks(client, auth_headers)
    plan_id = generated["plan_id"]
    task_id = generated["plan"]["tasks"][0]["id"]
    started = datetime.now(UTC) - timedelta(seconds=90)
    finished = datetime.now(UTC)
    _patch_task(
        client,
        auth_headers,
        plan_id,
        task_id,
        {
            "completed": True,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
        },
    )

    execution = _latest_execution(task_id)
    assert execution is not None
    # 90s -> 2 whole minutes (rounded up, never 0).
    assert execution.actual_duration == 2


def test_estimate_accuracy_endpoint_aggregates_by_day(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _plan_with_tasks(client, auth_headers, minutes=30)
    plan_id = generated["plan_id"]
    tasks = generated["plan"]["tasks"]
    assert tasks
    today = date.today().isoformat()
    for task in tasks:
        _patch_task(
            client, auth_headers, plan_id, task["id"], {"scheduled_date": today}
        )
    executed = tasks[0]
    _patch_task(
        client,
        auth_headers,
        plan_id,
        executed["id"],
        {"completed": True, "actual_duration": 45},
    )

    response = client.get(
        "/api/v1/users/me/estimate-accuracy?days=7", headers=auth_headers
    )
    assert response.status_code == 200, response.text
    points = {item["date"]: item for item in response.json()}
    assert today in points
    point = points[today]
    planned = sum(task["estimated_duration"] for task in tasks)
    assert point["planned_minutes"] == planned
    assert point["actual_minutes"] == 45
    assert point["ratio"] == round(45 / planned, 3)

    insights = client.get(
        f"/api/v1/plans/{plan_id}/insights", headers=auth_headers
    ).json()
    assert insights["estimate_accuracy_ratio"] == round(45 / planned, 3)
    daily = next(item for item in insights["daily"] if item["date"] == today)
    assert daily["actual_minutes"] == 45
    assert daily["estimate_accuracy_ratio"] == round(45 / planned, 3)


def test_estimate_accuracy_rejects_out_of_range_days(
    client: TestClient, auth_headers: dict
) -> None:
    response = client.get(
        "/api/v1/users/me/estimate-accuracy?days=0", headers=auth_headers
    )
    assert response.status_code == 422


def test_postpone_falls_back_to_micro_adjust_when_tomorrow_is_full(
    client: TestClient, auth_headers: dict
) -> None:
    preferences = {
        "available_minutes_per_day": 30,
        "daily_limit_minutes": 30,
        "buffer_minutes": 0,
        "high_cognitive_max_per_day": 2,
    }
    updated = client.put(
        "/api/v1/users/me/preferences", json=preferences, headers=auth_headers
    )
    assert updated.status_code == 200, updated.text

    generated = _plan_with_tasks(client, auth_headers, minutes=60)
    plan_id = generated["plan_id"]
    task = generated["plan"]["tasks"][0]
    today = date.today()
    _patch_task(
        client,
        auth_headers,
        plan_id,
        task["id"],
        {"scheduled_date": today.isoformat(), "estimated_duration": 60},
    )

    body = _submit_feedback(client, auth_headers, plan_id, completion_rate=0.0)
    assert body["replan_decision"] == "micro_adjust"
    assert body["postponed_task_ids"] == []
    assert body["adjustment"] is not None


def test_postpone_moves_todays_unfinished_tasks_to_tomorrow(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _plan_with_tasks(client, auth_headers)
    plan_id = generated["plan_id"]
    task = generated["plan"]["tasks"][0]
    today = date.today()
    _patch_task(
        client,
        auth_headers,
        plan_id,
        task["id"],
        {"scheduled_date": today.isoformat()},
    )

    body = _submit_feedback(client, auth_headers, plan_id, completion_rate=0.0)
    assert body["replan_decision"] == "postpone"
    assert body["replan_triggered"] is False
    assert task["id"] in body["postponed_task_ids"]

    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    moved = next(item for item in detail["tasks"] if item["id"] == task["id"])
    assert moved["scheduled_date"] == (today + timedelta(days=1)).isoformat()
    assert detail["version"] == 1

    # Idempotent: a second check-in on the same day must not move it again.
    repeat = _submit_feedback(client, auth_headers, plan_id, completion_rate=0.0)
    assert repeat["replan_decision"] == "postpone"
    assert repeat["postponed_task_ids"] == []
    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    still = next(item for item in detail["tasks"] if item["id"] == task["id"])
    assert still["scheduled_date"] == (today + timedelta(days=1)).isoformat()
