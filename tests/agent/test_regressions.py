"""Regression guards for the A-class defects fixed after the P0 review.

Each test would fail if the corresponding defect came back.
"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.agent.context import CurrentPlanSnapshot, CurrentTaskSnapshot
from app.agent.graph import PlannerGraph
from app.agent.nodes._shared import compute_confidence
from app.agent.nodes.prediction import _task_features
from app.agent.schemas import GoalAnalysisResult, PlanGenerationResult, UserSituationResult
from app.agent.state import AgentConfig, PlannerContext, PlannerRequest
from app.core.config import Settings
from app.domain.models.enums import TaskStatus
from app.domain.rules.base import RuleEngine
from app.domain.scheduling.scheduler import Scheduler
from app.ml.adjustment import RuleBasedAdjustmentPredictor
from app.ml.base import AdjustmentRequest, AdjustmentRoute, FeedbackSignal, UserFeatureSet
from app.ml.predictors import PredictorSet
from tests.agent.conftest import CHECKPOINTER, override_plan_service, preview_of


# ---------------------------------------------------------------------------
# A1 - AGENT_MAX_REPAIR_ATTEMPTS must reach the state
# ---------------------------------------------------------------------------
def test_repair_budget_comes_from_config() -> None:
    ctx = PlannerContext(
        scheduler=Scheduler(),
        rule_engine=RuleEngine(),
        predictors=PredictorSet.default(),
        config=AgentConfig(max_repair_attempts=7),
        llm=None,
        context_builder=None,
    )
    graph = PlannerGraph(ctx, checkpointer=CHECKPOINTER)
    request = PlannerRequest(user_id=1, start_date=date.today(), end_date=date.today())
    state = graph._seed_state(request, graph_version="test", run_id="r1")
    # Was hardcoded to 2 before the fix, silently ignoring the setting.
    assert state["max_repair_attempts"] == 7


# ---------------------------------------------------------------------------
# A2 - confidence is derived, not hardcoded to 0.5
# ---------------------------------------------------------------------------
def test_compute_confidence_averages_the_analysis_stages() -> None:
    state = {
        "goal_analysis": GoalAnalysisResult(confidence=0.6),
        "user_situation": UserSituationResult(confidence=0.8),
        "plan_draft": PlanGenerationResult(confidence=0.4),
    }
    assert compute_confidence(state) == 0.6  # mean(0.6, 0.8, 0.4)


def test_compute_confidence_defaults_when_nothing_reports() -> None:
    assert compute_confidence({}) == 0.5


def test_preview_and_plan_share_the_same_confidence(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    override_plan_service(client)
    body = preview_of(client, auth_headers, preview_payload)
    preview_confidence = body["preview"]["confidence"]

    # Regression guard: this used to be a hardcoded 0.5 everywhere.
    assert preview_confidence != 0.5

    confirmed = client.post(
        f"/api/v1/plans/preview/{body['thread_id']}/confirm", headers=auth_headers
    )
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["plan"]["confidence"] == preview_confidence


# ---------------------------------------------------------------------------
# A4 - the adjustment request must carry task features in the feedback graph
# ---------------------------------------------------------------------------
def test_task_features_fall_back_to_the_current_plan() -> None:
    state = {
        "current_plan": CurrentPlanSnapshot(
            plan_id=1,
            version=1,
            tasks=[
                CurrentTaskSnapshot(
                    task_id=42,
                    title="数学",
                    status=TaskStatus.SCHEDULED,
                    estimated_duration=90,
                    subject="math",
                )
            ],
        )
    }
    features = _task_features(state)  # type: ignore[arg-type]
    assert len(features) == 1
    assert features[0].task_id == 42  # real id in the feedback graph
    assert features[0].estimated_duration_minutes == 90


# ---------------------------------------------------------------------------
# A5 - degradation is surfaced, never silent
# ---------------------------------------------------------------------------
class _BrokenContextBuilder:
    def build(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("simulated database outage")


def test_preview_reports_a_failing_context_builder(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    override_plan_service(client, context_builder=_BrokenContextBuilder())
    body = preview_of(client, auth_headers, preview_payload)

    assert body["degraded"] is True
    assert any("context_build_failed" in warning for warning in body["warnings"])
    # Degraded must still be usable - the user gets a plan, plus an explanation.
    assert body["preview"]["tasks"]

    confirmed = client.post(
        f"/api/v1/plans/preview/{body['thread_id']}/confirm", headers=auth_headers
    )
    assert confirmed.status_code == 201
    assert confirmed.json()["degraded"] is True


def test_healthy_preview_is_not_flagged_as_degraded(
    client: TestClient, auth_headers: dict, preview_payload: dict
) -> None:
    override_plan_service(client)
    body = preview_of(client, auth_headers, preview_payload)
    assert body["degraded"] is False
    assert body["warnings"] == []


# ---------------------------------------------------------------------------
# A6 - a single bad day must not trigger a full rebuild
# ---------------------------------------------------------------------------
def _adjustment_request(signals: list[FeedbackSignal]) -> AdjustmentRequest:
    return AdjustmentRequest(
        user=UserFeatureSet(user_id=1),
        recent_feedback=signals,
    )


def test_one_bad_day_lightens_the_load_instead_of_rebuilding() -> None:
    request = _adjustment_request(
        [FeedbackSignal(date=date.today(), completion_rate=0.4, stress_level=8, energy_level=3)]
    )
    prediction = RuleBasedAdjustmentPredictor().predict_adjustment(request)
    assert prediction.route is AdjustmentRoute.MICRO_ADJUST
    assert prediction.severity.value == "HIGH"
    assert any("check-in" in reason for reason in prediction.reasons)


def test_sustained_low_completion_triggers_a_rebuild() -> None:
    signals = [
        FeedbackSignal(date=date(2026, 9, day), completion_rate=0.4) for day in (18, 19, 20)
    ]
    prediction = RuleBasedAdjustmentPredictor().predict_adjustment(
        _adjustment_request(signals)
    )
    assert prediction.route is AdjustmentRoute.FULL_REPLAN


def test_no_feedback_is_no_change() -> None:
    prediction = RuleBasedAdjustmentPredictor().predict_adjustment(_adjustment_request([]))
    assert prediction.route is AdjustmentRoute.NO_CHANGE
    assert prediction.source == "fallback:rule"


# ---------------------------------------------------------------------------
# D1 - the Postgres checkpointer must own a live pool, not a dropped Connection
# ---------------------------------------------------------------------------
class _FakePool:
    def __init__(self, conninfo, **kwargs):  # noqa: ANN003
        self.conninfo = conninfo
        self.kwargs = kwargs
        self.opened = False
        self.closed = False

    def open(self, **kwargs):  # noqa: ANN003
        self.opened = True
        self.open_kwargs = kwargs

    def close(self):
        self.closed = True


def test_postgres_checkpointer_uses_a_pool_that_outlives_the_factory(monkeypatch) -> None:
    """Regression guard for ``psycopg.OperationalError: the connection is closed``.

    The old code called ``PostgresSaver.from_conn_string(dsn).__enter__()`` and
    dropped the generator-based context manager, so the connection closed as soon
    as it was collected. The factory must instead retain an open pool.
    """
    import gc

    # Import the real module first: its _internal submodule subscripts
    # ConnectionPool at import time, so the fake pool must be installed after.
    import langgraph.checkpoint.postgres  # noqa: F401
    from langgraph.checkpoint.memory import InMemorySaver

    from app.agent import checkpointer as cp

    recorded: dict = {}

    class _FakeSaver:
        def __init__(self, conn, serde=None):
            self.conn = conn
            self.serde = serde

        def setup(self):
            recorded["setup_called"] = True

    monkeypatch.setattr("psycopg_pool.ConnectionPool", _FakePool)
    monkeypatch.setattr("langgraph.checkpoint.postgres.PostgresSaver", _FakeSaver)

    settings = Settings(
        database_url="postgresql+psycopg://planner:planner@127.0.0.1:5432/planner",
        agent_checkpointer="postgres",
    )
    try:
        saver = cp.build_checkpointer(settings)
        gc.collect()  # would have closed the old generator-held connection

        assert not isinstance(saver, InMemorySaver)
        assert isinstance(saver.conn, _FakePool)
        assert saver.conn.opened is True
        assert saver.conn.closed is False  # must survive the factory returning
        assert recorded.get("setup_called") is True
        assert saver.conn.conninfo == "postgresql://planner:planner@127.0.0.1:5432/planner"
    finally:
        cp.close_checkpointer()

    assert saver.conn.closed is True
    assert cp.get_checkpointer_mode() == "memory"


def test_postgres_checkpointer_degrades_to_memory_when_pool_cannot_open(
    monkeypatch,
) -> None:
    """An unreachable database must not block startup - it degrades, loudly."""
    import langgraph.checkpoint.postgres  # noqa: F401
    from langgraph.checkpoint.memory import InMemorySaver

    from app.agent import checkpointer as cp

    class _BoomPool:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            pass

        def open(self, **kwargs):  # noqa: ANN003
            raise RuntimeError("simulated database outage")

        def close(self):
            pass

    monkeypatch.setattr("psycopg_pool.ConnectionPool", _BoomPool)

    saver = cp.build_checkpointer(
        Settings(
            database_url="postgresql+psycopg://planner:planner@127.0.0.1:5432/planner",
            agent_checkpointer="postgres",
        )
    )
    assert isinstance(saver, InMemorySaver)
    assert cp.get_checkpointer_mode() == "memory"
