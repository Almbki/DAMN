"""Fixtures for the agent tests.

The agent is exercised through the real HTTP API so the graph, deterministic
policy, tools and persistence are covered together. There are no production
mock predictors: forcing a route is done by replacing the pure domain policy in
the node module for the duration of a test.
"""

from __future__ import annotations

import time
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.agent.checkpointer import build_checkpointer
from app.agent.state import AgentConfig
from app.api.deps import get_generation_service, get_plan_service
from app.application.services.plan_service import PlanService
from app.core.config import get_settings
from app.domain.feedback.models import (
    AdjustmentDecision,
    AdjustmentRoute,
    AdjustmentSeverity,
)
from app.main import app

CHECKPOINTER = build_checkpointer()
get_settings.cache_clear()

#: Original policy function, restored after every test.
_ORIGINAL_DECIDE = None


def override_plan_service(
    client: TestClient,
    *,
    route: AdjustmentRoute = AdjustmentRoute.NO_CHANGE,
    severity: AdjustmentSeverity = AdjustmentSeverity.NONE,
    max_preview_adjustments: int = 2,
    max_repair_attempts: int = 2,
    context_builder=None,
    plan_service_factory=None,
) -> None:
    """Force the deterministic adjustment route for the next requests.

    Overrides BOTH the request-scoped ``get_plan_service`` and the worker's
    ``get_generation_service`` factory: async jobs run on a background thread.
    """
    global _ORIGINAL_DECIDE

    import app.agent.nodes.adjustment_decision as adj

    if _ORIGINAL_DECIDE is None:
        _ORIGINAL_DECIDE = adj.decide_adjustment

    def fixed(**kwargs):  # noqa: ANN003
        return AdjustmentDecision(
            route=route,
            severity=severity,
            confidence=0.9,
            reasons=(f"test route {route.value}",),
            source="test:override",
        )

    adj.decide_adjustment = fixed

    from fastapi import Depends
    from sqlalchemy.orm import Session

    from app.agent.llm import StructuredLLM
    from app.api.deps import get_db
    from app.application.services.generation_service import GenerationService
    from app.infrastructure.database import SessionLocal

    def build(db: Session) -> PlanService:
        return PlanService(
            db,
            llm=StructuredLLM(None),  # deterministic fallback path
            checkpointer=CHECKPOINTER,
            context_builder=context_builder,
            config=AgentConfig(
                max_preview_adjustments=max_preview_adjustments,
                max_repair_attempts=max_repair_attempts,
            ),
        )

    def factory(db: Session = Depends(get_db)) -> PlanService:
        return build(db)

    app.dependency_overrides[get_plan_service] = factory
    generation_service = GenerationService(service_factory=lambda: build(SessionLocal()))
    app.dependency_overrides[get_generation_service] = lambda: generation_service


@pytest.fixture(autouse=True)
def _reset_overrides():
    global _ORIGINAL_DECIDE
    yield
    app.dependency_overrides.pop(get_plan_service, None)
    app.dependency_overrides.pop(get_generation_service, None)
    if _ORIGINAL_DECIDE is not None:
        import app.agent.nodes.adjustment_decision as adj

        adj.decide_adjustment = _ORIGINAL_DECIDE
        _ORIGINAL_DECIDE = None


@pytest.fixture()
def goals() -> list[dict]:
    return [
        {
            "title": "复习高数极限",
            "description": "看课\n做例题\n做练习",
            "subject": "math",
            "estimated_minutes": 120,
            "priority": 3,
        },
        {
            "title": "算法刷题",
            "description": "做两题\n复盘",
            "subject": "algorithm",
            "estimated_minutes": 90,
            "priority": 2,
        },
    ]


@pytest.fixture()
def preview_payload(goals: list[dict]) -> dict:
    return {
        "goals": goals,
        "plan_title": "Agent Test Plan",
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=13)).isoformat(),
    }


def run_job(client: TestClient, headers: dict, job_id: str, *, timeout: float = 120.0) -> dict:
    deadline = time.time() + timeout
    while True:
        response = client.get(f"/api/v1/plans/generation/{job_id}", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        if body["status"] in {"completed", "failed"}:
            return body
        assert time.time() < deadline, f"job {job_id} still {body['status']}"
        time.sleep(0.05)


def preview_of(client: TestClient, headers: dict, payload: dict) -> dict:
    response = client.post("/api/v1/plans/preview", json=payload, headers=headers)
    assert response.status_code == 202, response.text
    job = response.json()
    body = run_job(client, headers, job["job_id"])
    assert body["status"] == "completed", body
    return body["result"]