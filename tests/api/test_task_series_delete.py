"""API tests for deleting a single task vs a whole recurring series."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.infrastructure.database import SessionLocal
from app.infrastructure.database.models.execution import TaskExecution as TaskExecutionORM
from tests.support import generate_and_wait, replan_and_wait


def _recurring_goal(title: str = "每日练习") -> dict:
    return {
        "title": title,
        "estimated_minutes": 30,
        "daily_target_minutes": 30,
        "planning_mode": "recurring",
        "recurrence_frequency": "daily",
        "recurrence_interval": 1,
        "start_date": date.today().isoformat(),
    }


def _generate(client: TestClient, headers: dict) -> dict:
    return generate_and_wait(
        client,
        headers,
        {
            "goals": [_recurring_goal()],
            "end_date": (date.today() + timedelta(days=4)).isoformat(),
        },
    )


def _detail(client: TestClient, headers: dict, plan_id: int) -> dict:
    response = client.get(f"/api/v1/plans/{plan_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_single_delete_removes_one_occurrence(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _generate(client, auth_headers)
    plan_id = generated["plan_id"]
    series_tasks = [
        task for task in generated["plan"]["tasks"] if task["series_id"] is not None
    ]
    assert len(series_tasks) >= 3
    target = series_tasks[0]

    deleted = client.delete(
        f"/api/v1/plans/{plan_id}/tasks/{target['id']}", headers=auth_headers
    )
    assert deleted.status_code == 204, deleted.text

    remaining = _detail(client, auth_headers, plan_id)["tasks"]
    remaining_ids = {task["id"] for task in remaining}
    assert target["id"] not in remaining_ids
    assert len(remaining) == len(generated["plan"]["tasks"]) - 1
    # The rest of the series is intact.
    assert all(
        task["id"] in remaining_ids
        for task in series_tasks
        if task["id"] != target["id"]
    )


def test_series_delete_removes_unfinished_occurrences_only(
    client: TestClient, auth_headers: dict
) -> None:
    generated = _generate(client, auth_headers)
    plan_id = generated["plan_id"]

    # Replan so there are two plan versions: deleting in v2 must not touch v1.
    replanned = replan_and_wait(
        client, auth_headers, plan_id, {"reason": "series delete test"}
    )
    new_plan_id = replanned["plan_id"]
    new_tasks = [
        task for task in _detail(client, auth_headers, new_plan_id)["tasks"]
        if task["series_id"] is not None
    ]
    assert len(new_tasks) >= 3
    completed = new_tasks[0]
    patched = client.patch(
        f"/api/v1/plans/{new_plan_id}/tasks/{completed['id']}",
        json={"completed": True, "actual_duration": 25},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text

    unfinished = [
        task
        for task in new_tasks
        if task["id"] != completed["id"] and task["status"] != "completed"
    ]
    assert unfinished

    response = client.delete(
        f"/api/v1/plans/{new_plan_id}/tasks/{completed['id']}"
        "?scope=series&reason=no%20longer%20needed",
        headers=auth_headers,
    )
    assert response.status_code == 204, response.text

    after = _detail(client, auth_headers, new_plan_id)["tasks"]
    after_ids = {task["id"] for task in after}
    assert completed["id"] in after_ids
    assert all(task["id"] not in after_ids for task in unfinished)
    completed_after = next(task for task in after if task["id"] == completed["id"])
    assert completed_after["status"] == "completed"

    # Execution rows survive the series delete.
    with SessionLocal() as session:
        executions = session.scalars(
            select(TaskExecutionORM).where(TaskExecutionORM.task_id == completed["id"])
        ).all()
    assert len(executions) == 1
    assert executions[0].completed is True

    # The previous plan version is untouched.
    old_after = _detail(client, auth_headers, plan_id)
    old_ids = {task["id"] for task in old_after["tasks"]}
    original_ids = {task["id"] for task in generated["plan"]["tasks"]}
    assert old_ids == original_ids


def test_series_scope_rejects_a_non_series_task(
    client: TestClient, auth_headers: dict
) -> None:
    generated = generate_and_wait(
        client,
        auth_headers,
        {"goals": [{"title": "一次性任务", "estimated_minutes": 30}]},
    )
    plan_id = generated["plan_id"]
    non_series = next(
        task for task in generated["plan"]["tasks"] if task["series_id"] is None
    )

    response = client.delete(
        f"/api/v1/plans/{plan_id}/tasks/{non_series['id']}?scope=series",
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text
