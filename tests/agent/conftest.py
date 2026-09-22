"""Fixtures for the agent tests.

The agent layer is exercised through the real HTTP API so the graph, router,
tools, ML adapters and persistence are all covered together.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.agent.checkpointer import build_checkpointer
from app.agent.state import AgentConfig
from app.api.deps import get_generation_service, get_plan_service
from app.application.services.plan_service import PlanService
from app.core.config import get_settings
from app.main import app
from app.ml.adjustment import MockAdjustmentPredictor
from app.ml.base import (
    AdjustmentRoute,
    AdjustmentSeverity,
    CompletionPrediction,
    DurationPrediction,
    PredictionRequest,
)
from app.ml.predictors import PredictorSet

CHECKPOINTER = build_checkpointer()
get_settings.cache_clear()


@dataclass(slots=True)
class RouteOverride:
    """Test fake for the ML duration/completion predictors.

    The statistical predictors are real code paths, but tests need deterministic
    numbers (an all-1.0 factor would hide the ML plumbing).
    """

    duration_minutes: int = 90
    factor: float = 1.5
    completion: float = 0.65

    def install(self, predictors: PredictorSet) -> None:
        # Capture as locals so the nested predictors close over them.
        factor = self.factor
        completion = self.completion

        class _Duration:
            name = "test-duration"

            def predict(self, request: PredictionRequest) -> DurationPrediction:
                return DurationPrediction(
                    theoretical_minutes=request.task.estimated_duration_minutes,
                    predicted_minutes=max(
                        1, int(round(request.task.estimated_duration_minutes * factor))
                    ),
                    factor=factor,
                    confidence=0.9,
                    source="test",
                )

        class _Completion:
            name = "test-completion"

            def predict(self, request: PredictionRequest) -> CompletionPrediction:
                return CompletionPrediction(
                    probability=completion, confidence=0.9, source="test"
                )

        predictors.duration = _Duration()  # type: ignore[assignment]
        predictors.completion = _Completion()  # type: ignore[assignment]


def make_predictors(
    route: AdjustmentRoute = AdjustmentRoute.NO_CHANGE,
    *,
    severity: AdjustmentSeverity = AdjustmentSeverity.NONE,
) -> PredictorSet:
    """Build a predictor set with a forced adjustment route."""
    predictors = PredictorSet.default()
    predictors.adjustment = MockAdjustmentPredictor(
        route, severity=severity, reasons=[f"test route {route.value}"]
    )
    return predictors


def override_plan_service(
    client: TestClient,
    *,
    route: AdjustmentRoute = AdjustmentRoute.NO_CHANGE,
    severity: AdjustmentSeverity = AdjustmentSeverity.NONE,
    max_preview_adjustments: int = 2,
    max_repair_attempts: int = 2,
    context_builder=None,
) -> None:
    """Force the agent's ML route / config for the next requests.

    Overrides BOTH the request-scoped ``get_plan_service`` and the worker's
    ``get_generation_service`` factory: the async preview/adjust jobs run on a
    background thread with their own session, so overriding only the request
    dependency would leave the job using the real (mock-LLM) service.
    """
    from fastapi import Depends
    from sqlalchemy.orm import Session

    from app.agent.llm import StructuredLLM
    from app.api.deps import get_db
    from app.application.services.generation_service import GenerationService
    from app.infrastructure.database import SessionLocal

    def build(db: Session) -> PlanService:
        predictors = make_predictors(route, severity=severity)
        RouteOverride().install(predictors)
        return PlanService(
            db,
            predictors=predictors,
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
    yield
    app.dependency_overrides.pop(get_plan_service, None)
    app.dependency_overrides.pop(get_generation_service, None)


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
    """Poll an async generation job to completion and return its status payload."""
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
    """Submit the async preview job and return its result (the preview payload)."""
    response = client.post("/api/v1/plans/preview", json=payload, headers=headers)
    assert response.status_code == 202, response.text
    job = response.json()
    body = run_job(client, headers, job["job_id"])
    assert body["status"] == "completed", body
    return body["result"]
