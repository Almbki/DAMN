"""Durable generation jobs: restart rehydration, latest-preview recovery, orphans."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.application.dto.generation import AgentEvent
from app.application.services.generation_service import (
    GenerationService,
    recover_orphaned_generation_jobs,
)
from app.domain.models import GenerationJobRecord
from app.infrastructure.database import session_scope
from app.infrastructure.database.repositories import GenerationJobRepository
from tests.support import wait_job

_ONE_GOAL = [
    {
        "title": "复习高数极限",
        "description": "看课\n做例题",
        "subject": "math",
        "estimated_minutes": 120,
        "priority": 3,
    }
]


def _start_preview(client: TestClient, headers: dict) -> dict:
    response = client.post("/api/v1/plans/preview", json={"goals": _ONE_GOAL}, headers=headers)
    assert response.status_code == 202, response.text
    body = wait_job(client, headers, response.json()["job_id"])
    assert body["status"] == "completed", body
    return body


def _second_user_headers(client: TestClient) -> dict:
    email = f"other_{uuid.uuid4().hex[:10]}@example.com"
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Other"},
    )
    assert registered.status_code == 201, registered.text
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _insert_job(user_id: int, *, status: str, event_node: str | None = None) -> str:
    job_id = uuid.uuid4().hex
    events = []
    if event_node is not None:
        events.append(
            AgentEvent.from_dict(
                {"event": "node.completed", "node": event_node, "summary": "done"}
            ).model_dump(mode="json")
        )
    with session_scope() as session:
        GenerationJobRepository(session).create(
            GenerationJobRecord(
                job_id=job_id,
                user_id=user_id,
                kind="preview",
                status=status,
                events=events,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
    return job_id


def test_completed_job_survives_a_restart_simulation(
    client: TestClient, auth_headers: dict, registered_user: dict
) -> None:
    """A fresh GenerationService (empty memory) rehydrates status/result/events."""
    user_id = registered_user["user"]["id"]
    body = _start_preview(client, auth_headers)

    fresh = GenerationService()  # simulates a new process: no in-memory jobs
    status = fresh.get_status(body["job_id"], user_id)

    assert status["status"] == "completed"
    assert status["result"]["thread_id"] == body["result"]["thread_id"]
    assert status["result"]["preview"]["tasks"]
    assert any(event.get("node") == "goal_analysis" for event in status["events"])

    job = fresh.get_job(body["job_id"], user_id)
    assert job.events, "persisted events must be rehydrated"


def test_latest_preview_is_current_users_and_requires_auth(
    client: TestClient, auth_headers: dict
) -> None:
    first = _start_preview(client, auth_headers)
    second = _start_preview(client, auth_headers)

    latest = client.get("/api/v1/plans/preview/latest", headers=auth_headers)
    assert latest.status_code == 200, latest.text
    payload = latest.json()
    assert payload["thread_id"] == second["result"]["thread_id"]
    assert payload["thread_id"] != first["result"]["thread_id"]
    assert payload["preview"]["tasks"]

    assert client.get("/api/v1/plans/preview/latest").status_code == 401

    # Another user's latest is their own (empty) list, never this user's job.
    other_headers = _second_user_headers(client)
    other = client.get("/api/v1/plans/preview/latest", headers=other_headers)
    assert other.status_code == 404


def test_orphaned_running_job_is_failed_and_replayed_safely(
    registered_user: dict,
) -> None:
    user_id = registered_user["user"]["id"]
    job_id = _insert_job(user_id, status="running", event_node="goal_analysis")

    fresh = GenerationService()
    frames = list(fresh.stream_sse(job_id, user_id))

    assert any("event: goal_analysis" in frame for frame in frames)
    assert "event: failed" in frames[-1]
    assert fresh.get_status(job_id, user_id)["status"] == "failed"


def test_startup_recovery_marks_leftover_running_jobs_failed(
    registered_user: dict,
) -> None:
    user_id = registered_user["user"]["id"]
    job_id = _insert_job(user_id, status="running")

    assert recover_orphaned_generation_jobs() >= 1

    status = GenerationService().get_status(job_id, user_id)
    assert status["status"] == "failed"
    assert "restart" in (status["error"] or "")
