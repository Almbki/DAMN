"""Request-level atomic clarification gate (API)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.agent.conftest import override_plan_service, run_job


def _preview(client: TestClient, headers: dict, payload: dict) -> dict:
    response = client.post("/api/v1/plans/preview", json=payload, headers=headers)
    assert response.status_code == 202, response.text
    body = run_job(client, headers, response.json()["job_id"])
    assert body["status"] == "completed", body
    return body["result"]


def _project_payload(*, clarifications: dict | None = None) -> dict:
    start = date.today() + timedelta(days=1)
    end = start + timedelta(days=10)
    goal = {
        "title": "30 天学高数",
        "planning_mode": "project",
        "start_date": start.isoformat(),
        "deadline": end.isoformat(),
        "estimated_minutes": 60,
    }
    if clarifications:
        goal["clarifications"] = clarifications
    return {
        "goals": [goal],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


def test_project_without_curriculum_returns_clarification_not_preview(
    client: TestClient, auth_headers: dict
) -> None:
    override_plan_service(client)

    result = _preview(client, auth_headers, _project_payload())

    assert result["preview"] is None
    assert result["clarification"]["status"] == "needs_clarification"
    assert result["clarification"]["questions"]
    assert all(q["goal_id"] == 1 for q in result["clarification"]["questions"])


def test_multi_goal_clarification_is_request_atomic(
    client: TestClient, auth_headers: dict
) -> None:
    override_plan_service(client)
    payload = _project_payload()
    payload["goals"].insert(
        0,
        {
            "title": "买酱油",
            "planning_mode": "one_off",
            "deadline": (date.today() + timedelta(days=1)).isoformat(),
        },
    )

    result = _preview(client, auth_headers, payload)

    # A ready goal must not produce a partial preview while B needs clarification.
    assert result["preview"] is None
    assert result["clarification"]["questions"]
    assert {q["goal_id"] for q in result["clarification"]["questions"]} == {2}


def test_clarification_answers_unlock_ready_plan(
    client: TestClient, auth_headers: dict
) -> None:
    override_plan_service(client)
    result = _preview(
        client,
        auth_headers,
        _project_payload(clarifications={"curriculum": "极限;导数;积分"}),
    )

    assert result["clarification"] is None
    assert result["preview"] is not None
    assert len(result["preview"]["tasks"]) == 3
    assert {task["series_id"] for task in result["preview"]["tasks"]} == {
        "goal-1-project"
    }


def test_capacity_shortage_persists_pending(
    client: TestClient, auth_headers: dict
) -> None:
    override_plan_service(client)
    start = date.today() + timedelta(days=1)
    payload = {
        "goals": [
            {
                "title": "大任务",
                "planning_mode": "one_off",
                "deadline": start.isoformat(),
                "estimated_minutes": 120,
            }
        ],
        "start_date": start.isoformat(),
        "end_date": start.isoformat(),
        "daily_limit_minutes": 60,
    }

    result = _preview(client, auth_headers, payload)
    confirmed = client.post(
        f"/api/v1/plans/preview/{result['thread_id']}/confirm",
        headers=auth_headers,
    )
    assert confirmed.status_code == 201, confirmed.text
    persisted = confirmed.json()["plan"]["tasks"]

    # The 120-minute task is chunked into 2 x 60 because the daily limit is 60.
    # One chunk fits; the other stays PENDING rather than being deleted.
    assert len(persisted) == 2
    assert any(task["status"] == "pending" for task in persisted)
    assert any(task["scheduled_date"] is None for task in persisted)
    parent = next(task for task in persisted if task["parent_task_id"] is None)
    child = next(task for task in persisted if task["parent_task_id"] is not None)
    assert child["parent_task_id"] == parent["id"]
    ordered = sorted(persisted, key=lambda task: task["chunk_index"])
    assert [task["chunk_index"] for task in ordered] == [0, 1]
    scheduled = next(task for task in persisted if task["scheduled_date"] is not None)
    pending = next(task for task in persisted if task["scheduled_date"] is None)
    assert scheduled["scheduling_reason"] is None
    assert pending["scheduling_reason"] is not None
    assert all(task["chunk_count"] == 2 for task in persisted)
    assert all(task["completed_chunks"] == 0 for task in persisted)
    assert all(task["work_unit_completed"] is False for task in persisted)


def test_chunk_completion_aggregates_work_unit(
    client: TestClient, auth_headers: dict
) -> None:
    override_plan_service(client)
    start = date.today() + timedelta(days=1)
    payload = {
        "goals": [
            {
                "title": "大任务",
                "planning_mode": "one_off",
                "deadline": start.isoformat(),
                "estimated_minutes": 120,
            }
        ],
        "start_date": start.isoformat(),
        "end_date": start.isoformat(),
        "daily_limit_minutes": 60,
    }
    preview = _preview(client, auth_headers, payload)
    confirmed = client.post(
        f"/api/v1/plans/preview/{preview['thread_id']}/confirm",
        headers=auth_headers,
    )
    assert confirmed.status_code == 201, confirmed.text
    plan = confirmed.json()["plan"]
    plan_id = plan["id"]
    chunks = sorted(plan["tasks"], key=lambda task: task["chunk_index"])
    assert len(chunks) == 2

    first = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{chunks[0]['id']}",
        json={"completed": True},
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text
    assert first.json()["completed_chunks"] == 1
    assert first.json()["work_unit_completed"] is False

    second = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{chunks[1]['id']}",
        json={"completed": True},
        headers=auth_headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["completed_chunks"] == 2
    assert second.json()["work_unit_completed"] is True

    fetched = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers)
    assert fetched.status_code == 200, fetched.text
    final_chunks = sorted(
        fetched.json()["tasks"], key=lambda task: task["chunk_index"]
    )
    assert [task["completed_chunks"] for task in final_chunks] == [2, 2]
    assert all(task["work_unit_completed"] for task in final_chunks)


def test_recurring_is_opaque_and_does_not_ask_for_internal_steps(
    client: TestClient, auth_headers: dict
) -> None:
    override_plan_service(client)
    start = date.today() + timedelta(days=1)
    end = start + timedelta(days=6)
    payload = {
        "goals": [
            {
                "title": "背考研单词",
                "planning_mode": "recurring",
                "recurrence_frequency": "daily",
                "start_date": start.isoformat(),
                "deadline": end.isoformat(),
                "daily_target_minutes": 20,
                "description": "新词\n复习\n遗忘曲线",
            }
        ],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }

    result = _preview(client, auth_headers, payload)

    assert result["clarification"] is None
    assert result["preview"] is not None
    assert len(result["preview"]["tasks"]) == 7
    assert all(task["standards"] == [] for task in result["preview"]["tasks"])
