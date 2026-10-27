"""API tests for goal sets (目标集), goal archive/restore and replan interaction."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.domain.models import Goal
from app.domain.models.enums import PlanningMode
from app.domain.recurrence import RecurrenceFrequency
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.models.execution import TaskExecution as TaskExecutionORM
from app.infrastructure.database.repositories import GoalRepository
from tests.agent.conftest import preview_of
from tests.support import generate_and_wait, replan_and_wait


def _register_and_login(client: TestClient, email: str) -> dict:
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "password123", "display_name": "Other"},
        ).status_code
        == 201
    )
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _recurring_goal(title: str) -> dict:
    return {
        "title": title,
        "estimated_minutes": 30,
        "daily_target_minutes": 30,
        "planning_mode": "recurring",
        "recurrence_frequency": "daily",
        "recurrence_interval": 1,
        "start_date": date.today().isoformat(),
    }


def _plan_tasks(client: TestClient, headers: dict, plan_id: int) -> list[dict]:
    response = client.get(f"/api/v1/plans/{plan_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["tasks"]


def _create_goal(client: TestClient, headers: dict, title: str) -> dict:
    response = client.post(
        "/api/v1/goals",
        json={"title": title, "estimated_minutes": 30},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Generation integration
# ---------------------------------------------------------------------------
def test_preview_batch_creates_one_goal_set(
    client: TestClient, auth_headers: dict
) -> None:
    result = preview_of(
        client,
        auth_headers,
        {
            "goals": [
                {"title": "批次目标 A", "estimated_minutes": 30},
                {"title": "批次目标 B", "estimated_minutes": 30},
            ],
            "plan_title": "Batch Group",
        },
    )
    set_id = result["goal_set_id"]
    assert set_id

    detail = client.get(f"/api/v1/goal-sets/{set_id}", headers=auth_headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["name"] == "Batch Group"
    assert body["goal_count"] == 2
    assert {goal["title"] for goal in body["goals"]} == {"批次目标 A", "批次目标 B"}
    assert all(goal["goal_set_id"] == set_id for goal in body["goals"])


def test_two_previews_create_two_goal_sets(
    client: TestClient, auth_headers: dict
) -> None:
    first = preview_of(
        client,
        auth_headers,
        {"goals": [{"title": "独立目标一", "estimated_minutes": 30}]},
    )
    second = preview_of(
        client,
        auth_headers,
        {"goals": [{"title": "独立目标二", "estimated_minutes": 30}]},
    )
    assert first["goal_set_id"] != second["goal_set_id"]

    listing = client.get("/api/v1/goal-sets", headers=auth_headers)
    assert listing.status_code == 200, listing.text
    ids = {item["id"] for item in listing.json()}
    assert {first["goal_set_id"], second["goal_set_id"]} <= ids


def test_existing_goal_set_id_attaches_new_preview_goals(
    client: TestClient, auth_headers: dict
) -> None:
    first = preview_of(
        client,
        auth_headers,
        {"goals": [{"title": "已有目标", "estimated_minutes": 30}]},
    )
    set_id = first["goal_set_id"]

    second = preview_of(
        client,
        auth_headers,
        {
            "goals": [{"title": "后续目标", "estimated_minutes": 30}],
            "goal_set_id": set_id,
        },
    )
    assert second["goal_set_id"] == set_id

    detail = client.get(f"/api/v1/goal-sets/{set_id}", headers=auth_headers).json()
    assert detail["goal_count"] == 2
    assert {goal["title"] for goal in detail["goals"]} == {"已有目标", "后续目标"}


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------
def test_goal_sets_are_user_scoped(
    client: TestClient, auth_headers: dict
) -> None:
    alice = auth_headers
    result = preview_of(
        client,
        alice,
        {"goals": [{"title": "Alice 目标集目标", "estimated_minutes": 30}]},
    )
    set_id = result["goal_set_id"]

    bob = _register_and_login(client, f"goal-set-bob-{uuid.uuid4().hex[:8]}@example.com")
    bob_list = client.get("/api/v1/goal-sets", headers=bob)
    assert bob_list.status_code == 200
    assert all(item["id"] != set_id for item in bob_list.json())

    assert client.get(f"/api/v1/goal-sets/{set_id}", headers=bob).status_code == 403


def test_cannot_archive_or_attach_another_users_set(
    client: TestClient, auth_headers: dict
) -> None:
    alice = auth_headers
    result = preview_of(
        client,
        alice,
        {"goals": [{"title": "Alice 私有", "estimated_minutes": 30}]},
    )
    set_id = result["goal_set_id"]
    detail = client.get(f"/api/v1/goal-sets/{set_id}", headers=alice).json()
    goal_id = detail["goals"][0]["id"]

    bob = _register_and_login(
        client, f"goal-set-bob2-{uuid.uuid4().hex[:8]}@example.com"
    )
    assert (
        client.post(f"/api/v1/goal-sets/{set_id}/archive", headers=bob).status_code
        == 403
    )
    attached = client.post(
        f"/api/v1/goal-sets/{set_id}/goals",
        json={"goal_ids": [goal_id]},
        headers=bob,
    )
    assert attached.status_code == 403


# ---------------------------------------------------------------------------
# Archive / restore semantics
# ---------------------------------------------------------------------------
def test_archive_single_goal_removes_only_its_unfinished_tasks(
    client: TestClient, auth_headers: dict
) -> None:
    end = (date.today() + timedelta(days=4)).isoformat()
    generated = generate_and_wait(
        client,
        auth_headers,
        {
            "goals": [
                _recurring_goal("每日背单词"),
                {"title": "写周报", "estimated_minutes": 30},
            ],
            "end_date": end,
        },
    )
    plan_id = generated["plan_id"]
    plan = generated["plan"]
    target_goal = next(goal for goal in plan["goals"] if goal["title"] == "每日背单词")
    other_goal = next(goal for goal in plan["goals"] if goal["title"] == "写周报")
    target_tasks = [task for task in plan["tasks"] if task["goal_id"] == target_goal["id"]]
    other_tasks = [task for task in plan["tasks"] if task["goal_id"] == other_goal["id"]]
    assert len(target_tasks) >= 3
    assert other_tasks

    completed = target_tasks[0]
    patched = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{completed['id']}",
        json={"completed": True, "actual_duration": 25},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text

    response = client.post(
        f"/api/v1/goals/{target_goal['id']}/archive", headers=auth_headers
    )
    assert response.status_code == 200, response.text
    impact = response.json()
    assert impact["goal_id"] == target_goal["id"]
    assert impact["removed_tasks"] == len(target_tasks) - 1
    assert impact["preserved_completed_tasks"] == 1

    remaining = _plan_tasks(client, auth_headers, plan_id)
    remaining_ids = {task["id"] for task in remaining}
    assert completed["id"] in remaining_ids
    assert all(task["id"] not in remaining_ids for task in target_tasks[1:])
    # The other goal is untouched.
    assert all(task["id"] in remaining_ids for task in other_tasks)

    # Execution history for the completed occurrence survives.
    with SessionLocal() as session:
        executions = session.scalars(
            select(TaskExecutionORM).where(TaskExecutionORM.task_id == completed["id"])
        ).all()
    assert len(executions) == 1
    assert executions[0].completed is True

    archived_goal = client.get(
        f"/api/v1/plans/{plan_id}", headers=auth_headers
    ).json()["goals"]
    assert next(g for g in archived_goal if g["id"] == target_goal["id"])["status"] == "archived"


def test_archive_whole_set_reports_impact_and_preserves_completed(
    client: TestClient, auth_headers: dict
) -> None:
    end = (date.today() + timedelta(days=3)).isoformat()
    generated = generate_and_wait(
        client,
        auth_headers,
        {
            "goals": [_recurring_goal("晨跑"), _recurring_goal("阅读")],
            "end_date": end,
        },
    )
    plan_id = generated["plan_id"]
    plan = generated["plan"]
    set_id = plan["goals"][0]["goal_set_id"]
    assert set_id
    tasks_by_goal = {
        goal["id"]: [task for task in plan["tasks"] if task["goal_id"] == goal["id"]]
        for goal in plan["goals"]
    }
    completed_ids: list[int] = []
    for goal in plan["goals"]:
        task = tasks_by_goal[goal["id"]][0]
        completed_ids.append(task["id"])
        patched = client.patch(
            f"/api/v1/plans/{plan_id}/tasks/{task['id']}",
            json={"completed": True, "actual_duration": 20},
            headers=auth_headers,
        )
        assert patched.status_code == 200, patched.text

    response = client.post(
        f"/api/v1/goal-sets/{set_id}/archive", headers=auth_headers
    )
    assert response.status_code == 200, response.text
    impact = response.json()
    assert impact["archived_goals"] == 2
    assert impact["preserved_completed_tasks"] == 2
    assert impact["removed_tasks"] == sum(
        len(tasks) - 1 for tasks in tasks_by_goal.values()
    )

    detail = client.get(f"/api/v1/goal-sets/{set_id}", headers=auth_headers).json()
    assert detail["status"] == "archived"
    assert detail["archived_at"] is not None
    assert all(goal["status"] == "archived" for goal in detail["goals"])

    remaining = _plan_tasks(client, auth_headers, plan_id)
    remaining_ids = {task["id"] for task in remaining}
    assert set(completed_ids) <= remaining_ids
    for tasks in tasks_by_goal.values():
        for task in tasks:
            if task["id"] in completed_ids:
                continue
            assert task["id"] not in remaining_ids

    # Plan version history stays readable and executions survive.
    assert client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).status_code == 200
    with SessionLocal() as session:
        executions = session.scalars(
            select(TaskExecutionORM).where(TaskExecutionORM.task_id.in_(completed_ids))
        ).all()
    assert {execution.task_id for execution in executions} == set(completed_ids)


def test_restore_single_goal_then_set_only_restores_archived_tasks(
    client: TestClient, auth_headers: dict
) -> None:
    end = (date.today() + timedelta(days=3)).isoformat()
    generated = generate_and_wait(
        client,
        auth_headers,
        {
            "goals": [_recurring_goal("目标 A"), _recurring_goal("目标 B")],
            "end_date": end,
        },
    )
    plan_id = generated["plan_id"]
    plan = generated["plan"]
    set_id = plan["goals"][0]["goal_set_id"]
    goal_a, goal_b = plan["goals"]
    tasks_a = [task for task in plan["tasks"] if task["goal_id"] == goal_a["id"]]
    tasks_b = [task for task in plan["tasks"] if task["goal_id"] == goal_b["id"]]

    assert (
        client.post(f"/api/v1/goal-sets/{set_id}/archive", headers=auth_headers).status_code
        == 200
    )

    restored = client.post(
        f"/api/v1/goals/{goal_a['id']}/restore", headers=auth_headers
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["restored_tasks"] == len(tasks_a)

    remaining_ids = {task["id"] for task in _plan_tasks(client, auth_headers, plan_id)}
    assert all(task["id"] in remaining_ids for task in tasks_a)
    assert all(task["id"] not in remaining_ids for task in tasks_b)

    detail = client.get(f"/api/v1/goal-sets/{set_id}", headers=auth_headers).json()
    statuses = {goal["id"]: goal["status"] for goal in detail["goals"]}
    assert statuses[goal_a["id"]] == "active"
    assert statuses[goal_b["id"]] == "archived"

    set_restore = client.post(
        f"/api/v1/goal-sets/{set_id}/restore", headers=auth_headers
    )
    assert set_restore.status_code == 200, set_restore.text
    assert set_restore.json()["restored_goals"] == 2

    remaining_ids = {task["id"] for task in _plan_tasks(client, auth_headers, plan_id)}
    assert all(task["id"] in remaining_ids for task in tasks_a)
    assert all(task["id"] in remaining_ids for task in tasks_b)
    detail = client.get(f"/api/v1/goal-sets/{set_id}", headers=auth_headers).json()
    assert detail["status"] == "active"
    assert all(goal["status"] == "active" for goal in detail["goals"])


# ---------------------------------------------------------------------------
# Replan interaction
# ---------------------------------------------------------------------------
def test_replan_preserves_goal_identity_and_excludes_archived_goals(
    client: TestClient, auth_headers: dict
) -> None:
    # Force chunking so goal A has several work units with a stable key.
    client.put(
        "/api/v1/users/me/preferences",
        json={
            "available_minutes_per_day": 30,
            "daily_limit_minutes": 30,
            "buffer_minutes": 0,
            "high_cognitive_max_per_day": 2,
        },
        headers=auth_headers,
    )
    generated = generate_and_wait(
        client,
        auth_headers,
        {
            "goals": [
                {"title": "保留目标", "estimated_minutes": 90},
                {"title": "归档目标", "estimated_minutes": 30},
            ]
        },
    )
    plan_id = generated["plan_id"]
    plan = generated["plan"]
    keep_goal = next(goal for goal in plan["goals"] if goal["title"] == "保留目标")
    archived_goal = next(goal for goal in plan["goals"] if goal["title"] == "归档目标")
    keep_tasks = [task for task in plan["tasks"] if task["goal_id"] == keep_goal["id"]]
    assert keep_tasks
    old_keys = {task["work_unit_key"] for task in keep_tasks if task["work_unit_key"]}
    assert old_keys

    completed = keep_tasks[0]
    patched = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{completed['id']}",
        json={"completed": True, "actual_duration": 30},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text
    assert (
        client.post(
            f"/api/v1/goals/{archived_goal['id']}/archive", headers=auth_headers
        ).status_code
        == 200
    )

    replanned = replan_and_wait(
        client, auth_headers, plan_id, {"reason": "goal set test"}
    )
    new_plan_id = replanned["plan_id"]
    new_plan = client.get(f"/api/v1/plans/{new_plan_id}", headers=auth_headers).json()

    new_goal_ids = {goal["id"] for goal in new_plan["goals"]}
    assert keep_goal["id"] in new_goal_ids
    assert archived_goal["id"] not in new_goal_ids
    assert all(task["goal_id"] != archived_goal["id"] for task in new_plan["tasks"])

    new_keep_tasks = [
        task for task in new_plan["tasks"] if task["goal_id"] == keep_goal["id"]
    ]
    assert new_keep_tasks
    new_keys = {task["work_unit_key"] for task in new_keep_tasks if task["work_unit_key"]}
    assert new_keys <= old_keys

    # The old version still shows the completed occurrence.
    old_tasks = _plan_tasks(client, auth_headers, plan_id)
    old_completed = next(task for task in old_tasks if task["id"] == completed["id"])
    assert old_completed["status"] == "completed"


# ---------------------------------------------------------------------------
# Idempotency / legacy rows
# ---------------------------------------------------------------------------
def test_repeated_archive_and_attach_are_idempotent(
    client: TestClient, auth_headers: dict
) -> None:
    first = _create_goal(client, auth_headers, "待归档目标一")
    second = _create_goal(client, auth_headers, "待归档目标二")
    created = client.post(
        "/api/v1/goal-sets",
        json={"name": "手动目标集"},
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    set_id = created.json()["id"]

    attached = client.post(
        f"/api/v1/goal-sets/{set_id}/goals",
        json={"goal_ids": [first["id"], second["id"]]},
        headers=auth_headers,
    )
    assert attached.status_code == 200, attached.text
    assert attached.json()["attached_goals"] == 2

    again = client.post(
        f"/api/v1/goal-sets/{set_id}/goals",
        json={"goal_ids": [first["id"], second["id"]]},
        headers=auth_headers,
    )
    assert again.json()["attached_goals"] == 0
    detail = client.get(f"/api/v1/goal-sets/{set_id}", headers=auth_headers).json()
    assert detail["goal_count"] == 2
    assert len(detail["goals"]) == 2

    archived = client.post(
        f"/api/v1/goal-sets/{set_id}/archive", headers=auth_headers
    )
    assert archived.status_code == 200
    repeated = client.post(
        f"/api/v1/goal-sets/{set_id}/archive", headers=auth_headers
    )
    assert repeated.status_code == 200
    assert repeated.json() == {
        "goal_set_id": set_id,
        "archived_goals": 0,
        "removed_tasks": 0,
        "preserved_completed_tasks": 0,
    }

    sets = client.get("/api/v1/goal-sets", headers=auth_headers).json()
    assert len([item for item in sets if item["id"] == set_id]) == 1
    active_only = client.get(
        "/api/v1/goal-sets?include_archived=false", headers=auth_headers
    ).json()
    assert all(item["id"] != set_id for item in active_only)


def test_legacy_goals_without_set_are_readable_and_not_merged(
    client: TestClient, auth_headers: dict
) -> None:
    legacy = _create_goal(client, auth_headers, "遗留目标")
    assert legacy["goal_set_id"] is None

    listed = client.get("/api/v1/goals", headers=auth_headers)
    assert listed.status_code == 200
    assert any(goal["id"] == legacy["id"] for goal in listed.json())

    created = client.post(
        "/api/v1/goal-sets", json={"name": "全新目标集"}, headers=auth_headers
    )
    set_id = created.json()["id"]
    detail = client.get(f"/api/v1/goal-sets/{set_id}", headers=auth_headers).json()
    assert detail["goal_count"] == 0
    assert detail["goals"] == []


# ---------------------------------------------------------------------------
# Repository regression: planning mode / recurrence fields were dropped
# ---------------------------------------------------------------------------
def test_goal_repository_persists_planning_and_recurrence_fields(
    registered_user: dict,
) -> None:
    user_id = registered_user["user"]["id"]
    with SessionLocal() as session:
        repo = GoalRepository(session)
        created = repo.create(
            Goal(
                user_id=user_id,
                title="repo create",
                planning_mode=PlanningMode.RECURRING,
                recurrence_frequency=RecurrenceFrequency.DAILY,
                recurrence_interval=2,
            )
        )
        many = repo.create_many(
            [
                Goal(
                    user_id=user_id,
                    title="repo create_many",
                    planning_mode=PlanningMode.PROJECT,
                    recurrence_frequency=RecurrenceFrequency.WEEKLY,
                    recurrence_interval=3,
                )
            ]
        )
        session.commit()
        created_id = created.id
        many_id = many[0].id

    with SessionLocal() as session:
        loaded = GoalRepository(session).get_by_id(created_id)
        loaded_many = GoalRepository(session).get_by_id(many_id)

    assert loaded is not None
    assert loaded.planning_mode == PlanningMode.RECURRING
    assert loaded.recurrence_frequency == RecurrenceFrequency.DAILY
    assert loaded.recurrence_interval == 2
    assert loaded_many is not None
    assert loaded_many.planning_mode == PlanningMode.PROJECT
    assert loaded_many.recurrence_frequency == RecurrenceFrequency.WEEKLY
    assert loaded_many.recurrence_interval == 3
