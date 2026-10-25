"""Phase 1 model wiring: record fields, four-section reflection, state history."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from app.application.services.user_model_service import UserModelService
from app.domain.models import DailyState
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import (
    DailyStateRepository,
    PredictionOutcomeRepository,
    PredictionSnapshotRepository,
    TaskRepository,
)
from tests.support import generate_and_wait, replan_and_wait


def _complete_assessment(client: TestClient, headers: dict) -> dict:
    body = client.post("/api/v1/users/me/trait-assessment/start", headers=headers).json()
    for _ in range(80):
        if body["status"] == "completed":
            return body
        item = body["next_item"]
        response = client.post(
            f"/api/v1/users/me/trait-assessment/{body['assessment_id']}/answer",
            json={"item_id": item["item_id"], "response": 3},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
    raise AssertionError("assessment did not complete")


def _user_id(client: TestClient, headers: dict) -> int:
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _generate(client: TestClient, headers: dict, title: str = "Phase1 task") -> dict:
    today = date.today()
    return generate_and_wait(
        client,
        headers,
        {
            "goals": [
                {
                    "title": title,
                    "estimated_minutes": 45,
                    "start_date": today.isoformat(),
                    "deadline": (today + timedelta(days=1)).isoformat(),
                }
            ],
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
        },
    )


def _patch(client: TestClient, headers: dict, plan_id: int, task_id: int, payload: dict) -> None:
    response = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}", json=payload, headers=headers
    )
    assert response.status_code == 200, response.text


def test_record_fields_and_reflection_reach_level2(
    client: TestClient, auth_headers: dict
) -> None:
    today = date.today()
    _complete_assessment(client, auth_headers)
    generated = _generate(client, auth_headers)
    plan_id = generated["plan_id"]
    task_id = generated["plan"]["tasks"][0]["id"]
    _patch(
        client,
        auth_headers,
        plan_id,
        task_id,
        {"difficulty": 4, "task_type": "reading", "value_score": 5},
    )
    feedback = client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        json={
            "date": today.isoformat(),
            "completion_rate": 0.8,
            "day_review": "today went okay",
            "stuck_points": "math proofs",
            "state_review": "a bit tired",
            "tomorrow_outlook": "plan less",
        },
        headers=auth_headers,
    )
    assert feedback.status_code == 201, feedback.text

    user_id = _user_id(client, auth_headers)
    session = SessionLocal()
    try:
        service = UserModelService(session)
        days = service.build_days(user_id)
        day_input = next(day for day in days if day.date == today)
        plan_input = next(
            plan for plan in day_input.task_plans if plan.task_id == str(task_id)
        )
        assert plan_input.difficulty == 4
        assert plan_input.deadline is not None
        assert plan_input.deadline >= plan_input.planned_start

        reflection = day_input.reflection
        assert reflection is not None
        assert reflection.day_review == "today went okay"
        assert reflection.stuck_points == "math proofs"
        assert reflection.state_review == "a bit tired"
        assert reflection.tomorrow_outlook == "plan less"

        task = TaskRepository(session).get_by_id(task_id)
        assert task is not None
        context = service.task_context(task)
        assert context.difficulty == 4
        assert context.task_type == "reading"
        assert context.deadline is not None
        # Level 3 compares the deadline with an aware UTC prediction timestamp.
        assert context.deadline.tzinfo is not None
    finally:
        session.close()


def test_free_text_still_falls_back_to_day_review(
    client: TestClient, auth_headers: dict
) -> None:
    today = date.today()
    _complete_assessment(client, auth_headers)
    generated = _generate(client, auth_headers)
    plan_id = generated["plan_id"]
    feedback = client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        json={
            "date": today.isoformat(),
            "completion_rate": 0.9,
            "free_text": "legacy free text",
        },
        headers=auth_headers,
    )
    assert feedback.status_code == 201, feedback.text
    user_id = _user_id(client, auth_headers)
    session = SessionLocal()
    try:
        days = UserModelService(session).build_days(user_id)
        day_input = next(day for day in days if day.date == today)
        assert day_input.reflection is not None
        assert day_input.reflection.day_review == "legacy free text"
    finally:
        session.close()


def test_refresh_persists_daily_states_and_prunes_180_days(
    client: TestClient, auth_headers: dict
) -> None:
    _complete_assessment(client, auth_headers)
    generated = _generate(client, auth_headers)
    plan_id = generated["plan_id"]
    task_id = generated["plan"]["tasks"][0]["id"]
    _patch(
        client,
        auth_headers,
        plan_id,
        task_id,
        {"completed": False, "completion_rate": 0.5, "actual_duration": 20},
    )
    user_id = _user_id(client, auth_headers)

    session = SessionLocal()
    try:
        service = UserModelService(session)
        snapshot = service.refresh_dynamic_state(user_id)
        assert snapshot is not None
        repo = DailyStateRepository(session)
        rows = repo.list_by_user(user_id)
        assert rows
        assert rows[0].date == snapshot.date
        assert rows[0].data_origin == "real"

        old_day = date.today() - timedelta(days=200)
        repo.upsert(
            DailyState(
                user_id=user_id,
                date=old_day,
                fatigue=0.1,
                stress=0.1,
                self_efficacy=0.5,
                fatigue_uncertainty=0.2,
                stress_uncertainty=0.2,
                self_efficacy_uncertainty=0.2,
            )
        )
        session.flush()
        assert repo.get_by_user_and_date(user_id, old_day) is not None

        service.refresh_dynamic_state(user_id)
        assert repo.get_by_user_and_date(user_id, old_day) is None
    finally:
        session.close()


def test_shadow_writes_prediction_snapshot_and_outcome(
    client: TestClient, auth_headers: dict
) -> None:
    today = date.today()
    _complete_assessment(client, auth_headers)
    generated = _generate(client, auth_headers, "Phase1 shadow")
    plan_id = generated["plan_id"]
    task_id = generated["plan"]["tasks"][0]["id"]
    _patch(
        client,
        auth_headers,
        plan_id,
        task_id,
        {"completed": False, "completion_rate": 0.5, "actual_duration": 20},
    )
    feedback = client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        json={
            "date": today.isoformat(),
            "completion_rate": 0.8,
            "stress_level": 5,
            "energy_level": 5,
        },
        headers=auth_headers,
    )
    assert feedback.status_code == 201, feedback.text

    replanned = replan_and_wait(client, auth_headers, plan_id, {"reason": "phase1 shadow"})
    new_plan_id = replanned["plan_id"]
    new_plan = client.get(f"/api/v1/plans/{new_plan_id}", headers=auth_headers).json()
    new_tasks = new_plan["tasks"]
    assert new_tasks

    session = SessionLocal()
    try:
        snapshots = PredictionSnapshotRepository(session)
        found = []
        for item in new_tasks:
            found.extend(snapshots.list_by_task(item["id"]))
        assert found, "Level 3 shadow should freeze prediction snapshots"
        target = found[0]
        assert target.feature_snapshot
        assert target.input_hash
        assert target.mode == "shadow"
        assert target.data_origin == "real"
        snapshot_id = target.id
        target_task_id = target.task_id
    finally:
        session.close()

    _patch(
        client,
        auth_headers,
        new_plan_id,
        target_task_id,
        {"completed": True, "actual_duration": 30},
    )

    session = SessionLocal()
    try:
        outcome = PredictionOutcomeRepository(session).get_by_snapshot(snapshot_id)
        assert outcome is not None
        assert outcome.completed is True
        assert outcome.actual_duration_minutes == 30.0
    finally:
        session.close()

def test_deadline_normalisation_matches_model_contracts() -> None:
    from app.application.services.user_model_service import (
        _as_deadline_naive,
        _as_deadline_utc,
    )

    # Level 2 TaskPlan compares the deadline with a naive planned_start.
    assert _as_deadline_naive(datetime(2030, 1, 1, 12, tzinfo=UTC)).tzinfo is None
    # A date-only deadline means the end of that day.
    assert _as_deadline_naive(date(2030, 1, 1)) == datetime(2030, 1, 1, 23, 59)
    assert _as_deadline_naive(None) is None

    # Level 3 compares the deadline with an aware UTC prediction timestamp.
    level3 = _as_deadline_utc(date(2030, 1, 1))
    assert level3 is not None and level3.tzinfo is not None
    assert _as_deadline_utc(datetime(2030, 1, 1, 12, tzinfo=UTC)).tzinfo is not None
    assert _as_deadline_utc(None) is None
