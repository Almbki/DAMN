"""Phase 4: daily-plan / unscheduled audit rows are persisted with the plan."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import (
    DailyPlanRepository,
    UnscheduledTaskRepository,
)
from tests.support import generate_and_wait

_REASONS = {"capacity", "deadline", "long_term_wait", "no_slot"}


def test_generated_plan_persists_daily_capacity_and_unscheduled_reasons(
    client: TestClient, auth_headers: dict
) -> None:
    generated = generate_and_wait(
        client,
        auth_headers,
        {
            "goals": [
                {"title": "Big project", "estimated_minutes": 600},
                {"title": "Small task", "estimated_minutes": 30},
            ],
            "start_date": date.today().isoformat(),
        },
    )
    plan_id = generated["plan_id"]
    plan_task_ids = {task["id"] for task in generated["plan"]["tasks"]}
    assert plan_task_ids

    session = SessionLocal()
    try:
        daily = DailyPlanRepository(session).list_by_plan(plan_id)
        unscheduled = UnscheduledTaskRepository(session).list_by_plan(plan_id)
    finally:
        session.close()

    assert daily, "the scheduler campaign should persist one row per day in the horizon"
    assert daily[0].capacity_minutes >= 0
    assert daily[0].used_minutes >= 0
    placed = {task_id for row in daily for task_id in row.tasks}
    assert placed <= plan_task_ids
    for row in unscheduled:
        assert row.task_id in plan_task_ids
        assert row.reason in _REASONS


def test_replan_keeps_per_version_schedule_audit(
    client: TestClient, auth_headers: dict
) -> None:
    from tests.support import replan_and_wait

    generated = generate_and_wait(
        client,
        auth_headers,
        {"goals": [{"title": "Stable task", "estimated_minutes": 60}],
         "start_date": date.today().isoformat()},
    )
    old_plan_id = generated["plan_id"]
    replanned = replan_and_wait(
        client, auth_headers, old_plan_id, {"reason": "phase4 audit"}
    )
    new_plan_id = replanned["plan_id"]

    session = SessionLocal()
    try:
        repo = DailyPlanRepository(session)
        old_rows = repo.list_by_plan(old_plan_id)
        new_rows = repo.list_by_plan(new_plan_id)
    finally:
        session.close()
    assert old_rows and new_rows
    assert {row.plan_id for row in old_rows} == {old_plan_id}
    assert {row.plan_id for row in new_rows} == {new_plan_id}
    # Versions are immutable: the previous version keeps its own audit rows.
    assert max(row.date for row in old_rows) <= max(row.date for row in new_rows)
