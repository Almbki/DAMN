"""Execution read-model and interruption semantics (null != observed zero)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import TaskExecutionRepository
from tests.support import generate_and_wait


def test_started_at_survives_get_and_clears_on_completion(
    client: TestClient, auth_headers: dict
) -> None:
    generated = generate_and_wait(
        client,
        auth_headers,
        {
            "goals": [
                {"title": "Started task", "estimated_minutes": 30},
                {"title": "Other task", "estimated_minutes": 30},
            ],
            "start_date": date.today().isoformat(),
        },
    )
    plan_id = generated["plan_id"]
    task = generated["plan"]["tasks"][0]
    started_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    response = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task['id']}",
        json={"started_at": started_at},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text

    fetched = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    fetched_task = next(item for item in fetched["tasks"] if item["id"] == task["id"])
    assert fetched_task["started_at"] is not None
    assert fetched_task["started_at"].startswith(started_at[:19])

    completed = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task['id']}",
        json={"completed": True, "actual_duration": 25, "interruption_count": 3},
        headers=auth_headers,
    )
    assert completed.status_code == 200, completed.text
    fetched = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    fetched_task = next(item for item in fetched["tasks"] if item["id"] == task["id"])
    assert fetched_task["started_at"] is None


def test_interruption_values_persist_as_observed_or_null(
    client: TestClient, auth_headers: dict
) -> None:
    generated = generate_and_wait(
        client,
        auth_headers,
        {
            "goals": [
                {"title": "Zero interruptions", "estimated_minutes": 20},
                {"title": "Three interruptions", "estimated_minutes": 20},
                {"title": "Missing interruptions", "estimated_minutes": 20},
            ],
            "start_date": date.today().isoformat(),
        },
    )
    plan_id = generated["plan_id"]
    tasks = generated["plan"]["tasks"]
    assert len(tasks) == 3

    def partial(task_id: int, payload: dict) -> None:
        response = client.patch(
            f"/api/v1/plans/{plan_id}/tasks/{task_id}",
            json={"completed": False, "completion_rate": 0.5, **payload},
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text

    partial(tasks[0]["id"], {"interruption_count": 0})
    partial(tasks[1]["id"], {"interruption_count": 3})
    partial(tasks[2]["id"], {})

    session = SessionLocal()
    try:
        repo = TaskExecutionRepository(session)
        zero = repo.list_by_task(tasks[0]["id"])[-1]
        three = repo.list_by_task(tasks[1]["id"])[-1]
        missing = repo.list_by_task(tasks[2]["id"])[-1]
    finally:
        session.close()

    assert zero.interruption_count == 0
    assert three.interruption_count == 3
    assert missing.interruption_count is None
    assert zero.completion_rate == 0.5
    assert zero.completed is False