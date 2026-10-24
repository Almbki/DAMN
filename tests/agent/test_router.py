"""Unit tests for the deterministic routing policy and edge helpers."""

from __future__ import annotations

from datetime import date

from app.agent.router import (
    AdjustmentRouter,
    route_after_adjustment,
    route_after_preview,
    should_repair,
)
from app.agent.state import PlannerRequest
from app.domain.feedback.adjustment import decide_adjustment
from app.domain.feedback.models import (
    AdjustmentDecision,
    AdjustmentRoute,
    AdjustmentSeverity,
)


def _decision(route: AdjustmentRoute) -> AdjustmentDecision:
    return AdjustmentDecision(
        route=route, severity=AdjustmentSeverity.LOW, source="policy:deterministic"
    )


def test_router_passes_through_policy_route_when_neutral() -> None:
    state = {
        "adjustment": _decision(AdjustmentRoute.MICRO_ADJUST),
        "current_plan": object(),
    }
    decision = AdjustmentRouter().decide(state)  # type: ignore[arg-type]
    assert decision.route is AdjustmentRoute.MICRO_ADJUST
    assert decision.overridden is False


def test_router_forces_replan_when_no_current_plan() -> None:
    state = {"adjustment": _decision(AdjustmentRoute.NO_CHANGE), "current_plan": None}
    decision = AdjustmentRouter().decide(state)  # type: ignore[arg-type]
    assert decision.route is AdjustmentRoute.FULL_REPLAN
    assert decision.overridden is True


def _request(intent) -> PlannerRequest:
    return PlannerRequest(
        user_id=1,
        plan_id=7,
        trigger_type=intent,
        start_date=date.today(),
        end_date=date.today(),
    )


def test_router_free_text_does_not_force_replan() -> None:
    from app.agent.schemas import RequestIntent

    state = {
        "adjustment": _decision(AdjustmentRoute.NO_CHANGE),
        "current_plan": object(),
        "request": _request(RequestIntent.FEEDBACK_DRIVEN),
        "user_adjustment": "please change everything",
    }
    decision = AdjustmentRouter().decide(state)  # type: ignore[arg-type]
    assert decision.route is AdjustmentRoute.NO_CHANGE
    assert decision.overridden is False


def test_router_explicit_manual_replan_wins() -> None:
    from app.agent.schemas import RequestIntent

    state = {
        "adjustment": _decision(AdjustmentRoute.NO_CHANGE),
        "current_plan": object(),
        "request": _request(RequestIntent.REPLAN_REQUEST),
    }
    decision = AdjustmentRouter().decide(state)  # type: ignore[arg-type]
    assert decision.route is AdjustmentRoute.FULL_REPLAN
    assert decision.overridden is True


def test_router_escalates_after_too_many_micro_adjustments() -> None:
    state = {
        "adjustment": _decision(AdjustmentRoute.MICRO_ADJUST),
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


# ---------------------------------------------------------------------------
# deterministic policy (replaces RuleBasedAdjustmentPredictor)
# ---------------------------------------------------------------------------
def test_no_feedback_is_no_change() -> None:
    decision = decide_adjustment(completion_rates=[])
    assert decision.route is AdjustmentRoute.NO_CHANGE
    assert decision.source == "fallback:no_data"


def test_one_bad_day_lightens_the_load_instead_of_rebuilding() -> None:
    decision = decide_adjustment(
        completion_rates=[0.4], stress_levels=[8], energy_levels=[3]
    )
    assert decision.route is AdjustmentRoute.MICRO_ADJUST
    assert decision.severity is AdjustmentSeverity.HIGH


def test_sustained_low_completion_proposes_a_full_replan() -> None:
    decision = decide_adjustment(completion_rates=[0.2, 0.3, 0.1])
    assert decision.route is AdjustmentRoute.FULL_REPLAN
    assert decision.source == "policy:deterministic"


def test_healthy_week_is_no_change() -> None:
    decision = decide_adjustment(
        completion_rates=[0.9, 0.95, 0.8], stress_levels=[3], energy_levels=[8]
    )
    assert decision.route is AdjustmentRoute.NO_CHANGE