"""Regression guards for the hardening pass.

Covers the DB-overflow clipping, the goal deadline date type, the SSE
`rule_validation` stage, and checkpointer pool replacement.
"""

from __future__ import annotations

from datetime import date, datetime

import langgraph.checkpoint.postgres  # noqa: F401  (import before patching the pool)
from langgraph.checkpoint.memory import InMemorySaver

from app.agent import checkpointer as cp
from app.agent.graph import PlannerGraph
from app.agent.schemas import PreviewPayload
from app.agent.state import AgentConfig, PlannerContext, PlannerRequest
from app.api.v1.mappers import preview_read
from app.application.services.plan_service import PlanService
from app.core.config import Settings
from app.domain.models.enums import ViolationSeverity
from app.domain.rules.base import RuleEngine, RuleViolation
from app.domain.scheduling.scheduler import Scheduler
from app.ml.predictors import PredictorSet
from app.schemas.common import ViolationRead
from app.schemas.goal import GoalDetailRead


def test_violation_read_accepts_a_domain_rule_violation() -> None:
    """`preview_read` maps RuleViolation (a Pydantic model) onto ViolationRead.

    Without ``from_attributes`` this raised a ValidationError -> HTTP 500 on
    /plans/preview, but only when a plan actually violated a hard rule (e.g.
    deadline_exceeded), which deterministic fallbacks never produced.
    """
    violation = RuleViolation(
        rule="deadline",
        severity=ViolationSeverity.HARD,
        task_ids=[3],
        message="task exceeds its deadline",
        code="deadline_exceeded",
    )

    read = ViolationRead.model_validate(violation)

    assert read.rule == "deadline"
    assert read.severity == "hard"
    assert read.task_ids == [3]
    assert read.code == "deadline_exceeded"


def test_preview_read_maps_rule_violations() -> None:
    """Guards the exact failing line: mappers.preview_read -> ViolationRead."""
    payload = PreviewPayload(
        thread_id="t",
        rule_violations=[
            RuleViolation(
                rule="deadline",
                task_ids=[1],
                message="task exceeds its deadline",
                code="deadline_exceeded",
            )
        ],
    )

    read = preview_read(payload)

    assert len(read.violations) == 1
    assert read.violations[0].code == "deadline_exceeded"
    assert read.violations[0].task_ids == [1]


def test_clip_truncates_to_the_column_width() -> None:
    assert PlanService._clip("a" * 300, 255) == "a" * 255
    assert PlanService._clip("  x  ", 255) == "x"
    assert PlanService._clip(None, 255) is None


def test_goal_deadline_serialises_as_a_plain_date() -> None:
    goal = GoalDetailRead.model_validate(
        {
            "id": 1,
            "title": "t",
            "deadline": datetime(2026, 10, 1, 12, 30),
            "created_at": datetime(2026, 9, 1, 9, 0),
        }
    )
    assert goal.deadline == date(2026, 10, 1)
    assert goal.model_dump(mode="json")["deadline"] == "2026-10-01"

    # A plain date (already coerced by a mapper) passes through unchanged.
    passthrough = GoalDetailRead.model_validate(
        {"id": 2, "title": "t", "deadline": date(2026, 10, 1), "created_at": datetime.now()}
    )
    assert passthrough.deadline == date(2026, 10, 1)


def test_run_events_include_the_rule_validation_stage() -> None:
    """The SSE layer re-emits `node.completed` as the stage name; rule_validation
    must publish one or a progress UI never advances past plan_generation."""
    ctx = PlannerContext(
        scheduler=Scheduler(),
        rule_engine=RuleEngine(),
        predictors=PredictorSet.default(),
        config=AgentConfig(),
        llm=None,
        context_builder=None,
    )
    graph = PlannerGraph(ctx, checkpointer=InMemorySaver())
    request = PlannerRequest(user_id=1, start_date=date.today(), end_date=date.today())

    _state, events = graph.run_with_events(request)

    assert any(
        event.get("event") == "node.completed" and event.get("node") == "rule_validation"
        for event in events
    )


def test_build_postgres_closes_the_replaced_pool(monkeypatch) -> None:
    class _Pool:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            self.closed = False

        def open(self, **kwargs) -> None:  # noqa: ANN003
            pass

        def close(self) -> None:
            self.closed = True

    class _Saver:
        def __init__(self, conn, serde=None) -> None:
            self.conn = conn
            self.serde = serde

        def setup(self) -> None:
            pass

    monkeypatch.setattr("psycopg_pool.ConnectionPool", _Pool)
    monkeypatch.setattr("langgraph.checkpoint.postgres.PostgresSaver", _Saver)

    settings = Settings(
        database_url="postgresql+psycopg://u:p@localhost:5432/db",
        agent_checkpointer="postgres",
    )
    try:
        first = cp.build_checkpointer(settings)
        second = cp.build_checkpointer(settings)
        assert first.conn.closed is True  # a replaced pool must not leak
        assert second.conn.closed is False
    finally:
        cp.close_checkpointer()
    assert second.conn.closed is True
