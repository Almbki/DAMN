"""Phase 1 API surface: optional record fields, execution semantics, events."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import TaskEventRepository, TaskExecutionRepository
from tests.support import generate_and_wait


def _plan_with_tasks(
    client: TestClient, headers: dict, goals: list[dict]
) -> dict:
    return generate_and_wait(
        client,
        headers,
        {"goals": goals, "start_date": date.today().isoformat()},
    )


def _last_execution(task_id: int):
    session = SessionLocal()
    try:
        return TaskExecutionRepository(session).list_by_task(task_id)[-1]
    finally:
        session.close()


def _task_events(task_id: int):
    session = SessionLocal()
    try:
        return TaskEventRepository(session).list_by_task(task_id)
    finally:
        session.close()


def test_task_record_fields_roundtrip(client: TestClient, auth_headers: dict) -> None:
    generated = _plan_with_tasks(
        client, auth_headers, [{"title": "Record fields", "estimated_minutes": 30}]
    )
    plan_id = generated["plan_id"]
    task_id = generated["plan"]["tasks"][0]["id"]
    payload = {
        "deadline": "2030-01-02",
        "earliest_start_date": "2030-01-01",
        "difficulty": 4,
        "task_type": "reading",
        "value_score": 5,
        "completion_criterion": "finish chapter 3 and write 3 notes",
    }
    response = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    for key, value in payload.items():
        assert body[key] == value, (key, body.get(key))

    fetched = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    stored = next(item for item in fetched["tasks"] if item["id"] == task_id)
    for key, value in payload.items():
        assert stored[key] == value, (key, stored.get(key))


def test_execution_status_is_derived_from_observed_outcome(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _plan_with_tasks(
        client,
        auth_headers,
        [
            {"title": "Started only", "estimated_minutes": 20},
            {"title": "Partial", "estimated_minutes": 20},
            {"title": "Done", "estimated_minutes": 20},
        ],
    )
    plan_id = generated["plan_id"]
    tasks = generated["plan"]["tasks"]
    assert len(tasks) == 3
    started_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    def patch(task_id: int, payload: dict) -> None:
        response = client.patch(
            f"/api/v1/plans/{plan_id}/tasks/{task_id}",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text

    patch(tasks[0]["id"], {"started_at": started_at})
    patch(
        tasks[1]["id"],
        {
            "completed": False,
            "completion_rate": 0.5,
            "failure_category": "scheduling",
            "estimate_feedback": "over",
        },
    )
    patch(tasks[2]["id"], {"completed": True, "actual_duration": 18})

    started_only = _last_execution(tasks[0]["id"])
    assert started_only.execution_status is None
    partial = _last_execution(tasks[1]["id"])
    assert partial.execution_status == "partial"
    assert partial.failure_category == "scheduling"
    assert partial.estimate_feedback == "over"
    done = _last_execution(tasks[2]["id"])
    assert done.execution_status == "completed"


def test_four_section_feedback_roundtrip(client: TestClient, auth_headers: dict) -> None:
    generated = _plan_with_tasks(
        client, auth_headers, [{"title": "Reflection", "estimated_minutes": 30}]
    )
    plan_id = generated["plan_id"]
    payload = {
        "date": date.today().isoformat(),
        "completion_rate": 1.0,
        "day_review": "today went okay",
        "stuck_points": "math proofs",
        "state_review": "a bit tired",
        "tomorrow_outlook": "plan less",
    }
    response = client.post(
        f"/api/v1/plans/{plan_id}/feedback", json=payload, headers=auth_headers
    )
    assert response.status_code == 201, response.text
    feedback = response.json()["feedback"]
    for key in ("day_review", "stuck_points", "state_review", "tomorrow_outlook"):
        assert feedback[key] == payload[key], (key, feedback.get(key))

    listed = client.get(
        f"/api/v1/plans/{plan_id}/feedback", headers=auth_headers
    ).json()
    assert listed[0]["day_review"] == payload["day_review"]


def test_task_events_are_appended_for_edits_and_delete(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _plan_with_tasks(
        client, auth_headers, [{"title": "Editable", "estimated_minutes": 30}]
    )
    plan_id = generated["plan_id"]
    task_id = generated["plan"]["tasks"][0]["id"]

    response = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}",
        json={"title": "Editable v2"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    events = _task_events(task_id)
    assert events[0].event_type == "edited"
    assert events[0].before == {"title": "Editable"}
    assert events[0].after == {"title": "Editable v2"}

    response = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}",
        json={"status": "skipped"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert _task_events(task_id)[0].event_type == "status_changed"

    response = client.delete(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}", headers=auth_headers
    )
    assert response.status_code == 204, response.text
    assert _task_events(task_id)[0].event_type == "deleted"
