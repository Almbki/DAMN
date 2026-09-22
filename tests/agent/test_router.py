"""Unit tests for the routing policy and conditional-edge helpers."""

from __future__ import annotations

from app.agent.router import (
    AdjustmentRouter,
    ClassifyPolicy,
    route_after_adjustment,
    route_after_preview,
    should_repair,
)
from app.agent.schemas import ClassifyResult, RequestIntent
from app.ml.base import (
    AdjustmentPrediction,
    AdjustmentRoute,
    AdjustmentSeverity,
    PlanProgress,
)


def _prediction(route: AdjustmentRoute) -> AdjustmentPrediction:
    return AdjustmentPrediction(route=route, severity=AdjustmentSeverity.LOW, source="test")


def test_router_passes_through_ml_route_when_policy_is_neutral() -> None:
    state = {
        "ml_prediction": _prediction(AdjustmentRoute.MICRO_ADJUST),
        "current_plan": object(),  # a plan exists
        "progress": PlanProgress(days_elapsed=0, completion_rate=0.0),
    }
    decision = AdjustmentRouter().decide(state)  # type: ignore[arg-type]
    assert decision.route is AdjustmentRoute.MICRO_ADJUST
    assert decision.overridden is False


def test_router_forces_replan_when_no_current_plan() -> None:
    state = {"ml_prediction": _prediction(AdjustmentRoute.NO_CHANGE), "current_plan": None}
    decision = AdjustmentRouter().decide(state)  # type: ignore[arg-type]
    assert decision.route is AdjustmentRoute.FULL_REPLAN
    assert decision.overridden is True


def test_router_user_note_wins() -> None:
    state = {
        "ml_prediction": _prediction(AdjustmentRoute.NO_CHANGE),
        "current_plan": object(),
        "user_adjustment": "please change everything",
    }
    decision = AdjustmentRouter().decide(state)  # type: ignore[arg-type]
    assert decision.route is AdjustmentRoute.FULL_REPLAN


def test_router_does_not_escalate_a_fresh_plan() -> None:
    """A brand-new plan has 0.0 completion for trivial reasons."""
    state = {
        "ml_prediction": _prediction(AdjustmentRoute.NO_CHANGE),
        "current_plan": object(),
        "progress": PlanProgress(days_elapsed=0, completion_rate=0.0),
    }
    decision = AdjustmentRouter().decide(state)  # type: ignore[arg-type]
    assert decision.route is AdjustmentRoute.NO_CHANGE


def test_router_escalates_a_persistently_failing_plan() -> None:
    state = {
        "ml_prediction": _prediction(AdjustmentRoute.MICRO_ADJUST),
        "current_plan": object(),
        "progress": PlanProgress(days_elapsed=4, completion_rate=0.1),
    }
    decision = AdjustmentRouter().decide(state)  # type: ignore[arg-type]
    assert decision.route is AdjustmentRoute.FULL_REPLAN
    assert decision.overridden is True


def test_router_escalates_after_too_many_micro_adjustments() -> None:
    state = {
        "ml_prediction": _prediction(AdjustmentRoute.MICRO_ADJUST),
        "current_plan": object(),
        "adjustment_count": 2,
    }
    decision = AdjustmentRouter().decide(state)  # type: ignore[arg-type]
    assert decision.route is AdjustmentRoute.FULL_REPLAN


def test_route_after_adjustment_maps_every_route() -> None:
    assert route_after_adjustment({"route": AdjustmentRoute.NO_CHANGE}) == "no_change"  # type: ignore[arg-type]
    assert route_after_adjustment({"route": AdjustmentRoute.MICRO_ADJUST}) == "micro_adjust"  # type: ignore[arg-type]
    assert route_after_adjustment({"route": AdjustmentRoute.FULL_REPLAN}) == "full_replan"  # type: ignore[arg-type]


def test_should_repair_respects_the_attempt_budget() -> None:
    violation = object()
    pending = {
        "rule_violations": [violation],
        "repair_attempts": 0,
        "max_repair_attempts": 2,
    }
    exhausted = {
        "rule_violations": [violation],
        "repair_attempts": 2,
        "max_repair_attempts": 2,
    }
    assert should_repair(pending) == "repair"  # type: ignore[arg-type]
    assert should_repair(exhausted) == "continue"  # type: ignore[arg-type]
    assert should_repair({"rule_violations": [], "repair_attempts": 0}) == "continue"  # type: ignore[arg-type]


def test_route_after_preview_confirm_vs_adjust() -> None:
    assert route_after_preview({}) == "finalize"  # type: ignore[arg-type]
    assert route_after_preview({"user_adjustment": "less work"}) == "revise"  # type: ignore[arg-type]


def test_classify_policy_paths() -> None:
    from datetime import date

    from app.agent.state import PlannerRequest

    initial = PlannerRequest(user_id=1, start_date=date.today(), end_date=date.today())
    intent, _confidence, _reasons = ClassifyPolicy.classify({"request": initial})  # type: ignore[arg-type]
    assert intent is RequestIntent.INITIAL_PLAN

    with_plan = PlannerRequest(
        user_id=1, plan_id=7, start_date=date.today(), end_date=date.today()
    )
    intent, _confidence, _reasons = ClassifyPolicy.classify({"request": with_plan})  # type: ignore[arg-type]
    assert intent is RequestIntent.REPLAN_REQUEST

    assert ClassifyResult(intent=intent).intent is intent
