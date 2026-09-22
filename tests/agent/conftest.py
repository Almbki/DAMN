"""Fixtures for the agent tests.

The agent layer is exercised through the real HTTP API so the graph, router,
tools, ML adapters and persistence are all covered together.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.agent.checkpointer import build_checkpointer
from app.agent.state import AgentConfig
from app.api.deps import get_plan_service
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

    Reuses the request-scoped session from ``get_db`` so the override never
    leaks a connection (SQLite would lock the test database). Pass
    ``context_builder`` to simulate a failing context (degradation path).
    """
    from fastapi import Depends
    from sqlalchemy.orm import Session

    from app.agent.llm import StructuredLLM
    from app.api.deps import get_db

    def factory(db: Session = Depends(get_db)) -> PlanService:
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

    app.dependency_overrides[get_plan_service] = factory


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.pop(get_plan_service, None)


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


def preview_of(client: TestClient, headers: dict, payload: dict) -> dict:
    response = client.post("/api/v1/plans/preview", json=payload, headers=headers)
    assert response.status_code == 202, response.text
    return response.json()
