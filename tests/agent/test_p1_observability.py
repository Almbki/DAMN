"""P1 observability tests: agent_runs, prediction_logs, agent_memories."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.agent.context import MemoryItem, MemoryKind
from app.application.context.repo_context_builder import merge_memory
from app.domain.models import AgentMemory
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import (
    AgentMemoryRepository,
    AgentRunRepository,
    PredictionLogRepository,
)
from app.ml.base import AdjustmentRoute
from tests.agent.conftest import override_plan_service, preview_of


def _user_id(client: TestClient, headers: dict) -> int:
    return client.get("/api/v1/users/me", headers=headers).json()["id"]


def _create_plan(client: TestClient, headers: dict, payload: dict) -> int:
    body = preview_of(client, headers, payload)
    confirmed = client.post(
        f"/api/v1/plans/preview/{body['thread_id']}/confirm", headers=headers
    )
    assert confirmed.status_code == 201, confirmed.text
    return confirmed.json()["plan"]["id"]


# ---------------------------------------------------------------------------
# agent_runs
# ---------------------------------------------------------------------------
def test_confirm_records_an_agent_run_with_nodes_and_plan_link(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    override_plan_service(client)
    user_id = _user_id(client, auth_headers)
    plan_id = _create_plan(client, auth_headers, preview_payload)

    session = SessionLocal()
    try:
        runs = AgentRunRepository(session).list_by_user(user_id)
    finally:
        session.close()

    plan_runs = [run for run in runs if run.plan_id == plan_id]
    assert plan_runs, "confirm must leave an agent_runs row linked to the plan"
    run = plan_runs[0]
    assert run.trigger_type == "confirm_preview"
    assert run.status == "completed"
    assert run.finished_at is not None
    # Resuming only re-runs the paused node and the finaliser.
    assert run.nodes_executed == ["preview", "plan_finalization"]
    assert run.graph_version and run.prompt_version
    summary = run.result_summary
    assert summary["plan_id"] == plan_id
    assert summary["version"] == 1
    assert summary["tasks"] == 2
    assert summary["confidence"] and summary["confidence"] != 0.5


def test_preview_run_is_traced_and_records_tool_calls(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    """The heavy work happens in the preview request, so its trace must exist."""
    override_plan_service(client, route=AdjustmentRoute.NO_CHANGE)
    user_id = _user_id(client, auth_headers)

    preview_of(client, auth_headers, preview_payload)

    session = SessionLocal()
    try:
        runs = AgentRunRepository(session).list_by_user(user_id)
    finally:
        session.close()

    run = next(run for run in runs if run.trigger_type == "initial_plan")
    assert run.status == "completed"
    for node in (
        "load_context",
        "goal_analysis",
        "theoretical_analysis",
        "plan_generation",
        "rule_validation",
        "preview",
    ):
        assert node in run.nodes_executed

    tools = {call.get("tool") for call in run.tool_calls}
    assert {"task_decomposer", "workload_estimator", "plan_drafter"} <= tools
    assert {"schedule_generator", "rule_validator"} <= tools
    # Only summaries and timings are recorded - no tool payloads.
    for call in run.tool_calls:
        assert set(call) == {"tool", "ok", "duration_ms", "summary"}


# ---------------------------------------------------------------------------
# prediction_logs
# ---------------------------------------------------------------------------
def test_confirm_logs_every_prediction_with_a_truthful_source(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    override_plan_service(client)
    plan_id = _create_plan(client, auth_headers, preview_payload)

    session = SessionLocal()
    try:
        logs = PredictionLogRepository(session).list_by_plan(plan_id)
    finally:
        session.close()

    assert logs, "persisting a plan must log its predictions"
    by_type = {log.prediction_type for log in logs}
    # duration + completion come from the predictors; time_slot from the same call.
    assert {"duration", "completion", "time_slot"} <= by_type

    for log in logs:
        assert log.source, "source must never be empty (no pretending it was ML)"
        assert log.feature_hash, "a feature fingerprint is required for drift analysis"
        assert log.task_id is not None
        assert log.predicted

    completion = next(log for log in logs if log.prediction_type == "completion")
    assert completion.predicted["probability"] == 0.65  # the test predictor's value


# ---------------------------------------------------------------------------
# agent_memories
# ---------------------------------------------------------------------------
def test_feedback_persists_memory(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    override_plan_service(client, route=AdjustmentRoute.NO_CHANGE)
    user_id = _user_id(client, auth_headers)
    plan_id = _create_plan(client, auth_headers, preview_payload)

    response = client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        json={"date": date.today().isoformat(), "completion_rate": 0.9},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text

    session = SessionLocal()
    try:
        memories = AgentMemoryRepository(session).list_by_user(user_id)
    finally:
        session.close()

    kinds = {memory.kind for memory in memories}
    assert "semantic" in kinds
    assert "episodic" in kinds
    assert all(memory.user_id == user_id for memory in memories)
    assert all(memory.key and memory.source for memory in memories)


def test_merge_memory_prefers_persisted_rows_and_keeps_derived_ones() -> None:
    derived = [
        MemoryItem(kind=MemoryKind.SEMANTIC, key="profile", summary="derived"),
        MemoryItem(kind=MemoryKind.SEMANTIC, key="extra", summary="derived-only"),
    ]
    stored = [
        AgentMemory(user_id=1, kind="semantic", key="profile", summary="stored", confidence=0.9)
    ]
    merged = {(item.kind, item.key): item for item in merge_memory(derived, stored)}

    assert merged[(MemoryKind.SEMANTIC, "profile")].summary == "stored"
    assert (MemoryKind.SEMANTIC, "extra") in merged  # derived-only survives


def test_merge_memory_ignores_unknown_kinds() -> None:
    stored = [AgentMemory(user_id=1, kind="not-a-kind", key="x")]
    assert merge_memory([], stored) == []


# ---------------------------------------------------------------------------
# evaluation script
# ---------------------------------------------------------------------------
def test_evaluation_script_returns_all_metrics(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    from scripts.evaluate_predictors import evaluate

    override_plan_service(client)
    user_id = _user_id(client, auth_headers)
    _create_plan(client, auth_headers, preview_payload)

    metrics = evaluate(user_id)
    names = {metric.name for metric in metrics}
    assert names == {
        "duration_mae_minutes",
        "completion_mae",
        "completion_brier",
        "stress_mae",
        "time_slot_error_rate",
    }
    # No executions were reported, so nothing is scored - and that must be
    # visible as n=0 rather than a fabricated number.
    duration = next(metric for metric in metrics if metric.name == "duration_mae_minutes")
    assert duration.n == 0
    assert duration.value is None
