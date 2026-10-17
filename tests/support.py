"""Shared helpers for exercising the async plan jobs through the HTTP API."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient


def wait_job(
    client: TestClient, headers: dict, job_id: str, timeout: float = 120
) -> dict:
    """Poll a generation job until it reaches a terminal status.

    Returns the full ``/plans/generation/{job_id}`` payload (status, result,
    error, events).
    """
    deadline = time.time() + timeout
    while True:
        response = client.get(f"/api/v1/plans/generation/{job_id}", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        if body["status"] in {"completed", "failed"}:
            return body
        assert time.time() < deadline, f"job {job_id} still {body['status']}"
        time.sleep(0.05)


def generate_and_wait(
    client: TestClient, headers: dict, payload: dict
) -> dict:
    """Submit ``POST /plans/generate``, wait for the job and fetch the plan."""
    response = client.post("/api/v1/plans/generate", json=payload, headers=headers)
    assert response.status_code == 202, response.text
    accepted = response.json()
    body = wait_job(client, headers, accepted["job_id"])
    assert body["status"] == "completed", body
    plan_id = body["result"]["plan_id"]
    detail = client.get(f"/api/v1/plans/{plan_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    return {
        "job_id": accepted["job_id"],
        "status": body["status"],
        "plan_id": plan_id,
        "events_url": accepted["events_url"],
        "plan": detail.json(),
    }


def replan_and_wait(
    client: TestClient, headers: dict, plan_id: int, payload: dict
) -> dict:
    """Submit ``POST /plans/{plan_id}/replan`` and return the job result."""
    response = client.post(
        f"/api/v1/plans/{plan_id}/replan", json=payload, headers=headers
    )
    assert response.status_code == 202, response.text
    accepted = response.json()
    body = wait_job(client, headers, accepted["job_id"])
    assert body["status"] == "completed", body
    return body["result"]


def decompose_and_wait(client: TestClient, headers: dict, payload: dict) -> dict:
    """Submit ``POST /plans/decompose`` and return the job result (the draft)."""
    response = client.post("/api/v1/plans/decompose", json=payload, headers=headers)
    assert response.status_code == 202, response.text
    accepted = response.json()
    body = wait_job(client, headers, accepted["job_id"])
    assert body["status"] == "completed", body
    return body["result"]
