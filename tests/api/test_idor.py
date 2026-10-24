"""Cross-user IDOR audit (User A must never read/write User B's resources)."""

from __future__ import annotations

from datetime import date, time

from fastapi.testclient import TestClient

from app.domain.models import ScheduleEvent
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import ScheduleEventRepository
from tests.support import generate_and_wait


def _register_and_login(client: TestClient, email: str) -> dict:
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Other"},
    ).status_code == 201
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_cross_user_resources_are_not_accessible(
    client: TestClient, auth_headers: dict
) -> None:
    alice = auth_headers
    alice_id = client.get("/api/v1/users/me", headers=alice).json()["id"]

    goal = client.post(
        "/api/v1/goals",
        json={"title": "Alice private goal", "estimated_minutes": 30},
        headers=alice,
    )
    assert goal.status_code == 201, goal.text
    goal_id = goal.json()["id"]

    generated = generate_and_wait(
        client,
        alice,
        {
            "goals": [{"title": "Alice private plan", "estimated_minutes": 30}],
            "start_date": date.today().isoformat(),
        },
    )
    plan_id = generated["plan_id"]
    task_id = generated["plan"]["tasks"][0]["id"]
    assert client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        json={"date": date.today().isoformat(), "completion_rate": 0.8},
        headers=alice,
    ).status_code == 201
    assessment = client.post(
        "/api/v1/users/me/trait-assessment/start", headers=alice
    ).json()

    session = SessionLocal()
    try:
        event = ScheduleEventRepository(session).upsert_by_uid(
            ScheduleEvent(
                user_id=alice_id,
                title="Alice private class",
                start_date=date.today(),
                start_time=time(8, 0),
                end_time=time(9, 0),
                source="manual",
                external_uid="alice-private-event",
            )
        )[0]
        session.commit()
        event_id = event.id
    finally:
        session.close()
    assert event_id is not None

    bob = _register_and_login(client, "idor-bob@example.com")

    # Plans / tasks / feedback / insights / replan.
    assert client.get(f"/api/v1/plans/{plan_id}", headers=bob).status_code == 403
    assert (
        client.get(f"/api/v1/plans/{plan_id}/changes", headers=bob).status_code == 403
    )
    assert (
        client.get(f"/api/v1/plans/{plan_id}/insights", headers=bob).status_code == 403
    )
    assert (
        client.get(f"/api/v1/plans/{plan_id}/feedback", headers=bob).status_code == 403
    )
    assert (
        client.post(
            f"/api/v1/plans/{plan_id}/feedback",
            json={"date": date.today().isoformat(), "completion_rate": 0.5},
            headers=bob,
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/plans/{plan_id}/tasks/{task_id}",
            json={"completed": True},
            headers=bob,
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/plans/{plan_id}/tasks/{task_id}", headers=bob
        ).status_code
        == 403
    )
    assert (
        client.get(f"/api/v1/plans/{plan_id}/replan/eligibility", headers=bob).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/plans/{plan_id}/replan",
            json={"reason": "takeover"},
            headers=bob,
        ).status_code
        == 403
    )

    # Goals.
    assert (
        client.patch(
            f"/api/v1/goals/{goal_id}", json={"title": "hijacked"}, headers=bob
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/goals/{goal_id}", headers=bob).status_code == 403

    # Level 1 assessment.
    assert (
        client.get(
            f"/api/v1/users/me/trait-assessment/{assessment['assessment_id']}",
            headers=bob,
        ).status_code
        == 404
    )

    # Schedule event.
    assert client.delete(f"/api/v1/schedules/{event_id}", headers=bob).status_code == 404
    bob_schedules = client.get("/api/v1/schedules", headers=bob)
    assert bob_schedules.status_code == 200
    assert all(item["id"] != event_id for item in bob_schedules.json())

    # Bob's plan list never contains Alice's plan.
    bob_plans = client.get("/api/v1/plans", headers=bob).json()
    assert all(item["id"] != plan_id for item in bob_plans)

    # Alice still has her schedule after Bob's failed delete.
    alice_schedules = client.get("/api/v1/schedules", headers=alice).json()
    assert any(item["id"] == event_id for item in alice_schedules)