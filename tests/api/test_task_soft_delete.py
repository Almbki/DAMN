"""API tests for soft-deleting a task.

Soft delete keeps ``tasks``, ``task_executions`` and ``task_standards`` rows so
the ML training data survives while the task disappears from reads/insights.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.infrastructure.database import SessionLocal
from app.infrastructure.database.models.execution import TaskExecution as TaskExecutionORM
from app.infrastructure.database.models.task_standard import TaskStandard as TaskStandardORM
from tests.support import generate_and_wait

_ONE_GOAL = [
    {
        "title": "复习高数极限",
        "description": "看课\n做例题",
        "subject": "math",
        "estimated_minutes": 120,
        "priority": 3,
    }
]


def _generate(client: TestClient, headers: dict) -> dict:
    return generate_and_wait(client, headers, {"goals": _ONE_GOAL, "plan_title": "Soft Delete"})


def test_delete_task_hides_it_and_is_idempotent(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _generate(client, auth_headers)
    plan_id = generated["plan_id"]
    tasks = generated["plan"]["tasks"]
    assert len(tasks) >= 1
    task_id = tasks[0]["id"]

    before = client.get(f"/api/v1/plans/{plan_id}/insights", headers=auth_headers).json()

    deleted = client.delete(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}?reason=no%20longer%20needed",
        headers=auth_headers,
    )
    assert deleted.status_code == 204, deleted.text

    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert all(task["id"] != task_id for task in detail.json()["tasks"])

    after = client.get(f"/api/v1/plans/{plan_id}/insights", headers=auth_headers).json()
    assert after["total_tasks"] == before["total_tasks"] - 1

    # Idempotent: deleting the already-deleted task still succeeds.
    again = client.delete(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}", headers=auth_headers
    )
    assert again.status_code == 204, again.text


def test_deleting_completed_task_preserves_execution_rows(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _generate(client, auth_headers)
    plan_id = generated["plan_id"]
    task_id = generated["plan"]["tasks"][0]["id"]

    completed = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}",
        json={"completed": True, "actual_duration": 75},
        headers=auth_headers,
    )
    assert completed.status_code == 200, completed.text

    deleted = client.delete(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}", headers=auth_headers
    )
    assert deleted.status_code == 204, deleted.text

    # The task is hidden ...
    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()
    assert all(task["id"] != task_id for task in detail["tasks"])
    insights = client.get(f"/api/v1/plans/{plan_id}/insights", headers=auth_headers).json()
    assert insights["total_actual_minutes"] == 0

    # ... but the execution / standards rows were NOT hard-deleted.
    with SessionLocal() as session:
        executions = session.scalars(
            select(TaskExecutionORM).where(TaskExecutionORM.task_id == task_id)
        ).all()
        assert len(executions) == 1
        assert executions[0].actual_duration == 75
        assert executions[0].completed is True

        standards = session.scalars(
            select(TaskStandardORM).where(TaskStandardORM.task_id == task_id)
        ).all()
        assert standards, "task standards must survive a soft delete"


def test_goal_with_only_deleted_tasks_can_be_deleted(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _generate(client, auth_headers)
    plan_id = generated["plan_id"]
    goal_id = generated["plan"]["goals"][0]["id"]

    for task in generated["plan"]["tasks"]:
        response = client.delete(
            f"/api/v1/plans/{plan_id}/tasks/{task['id']}", headers=auth_headers
        )
        assert response.status_code == 204, response.text

    response = client.delete(f"/api/v1/goals/{goal_id}", headers=auth_headers)
    assert response.status_code == 204, response.text
