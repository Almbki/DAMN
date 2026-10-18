"""Adjustment routing policy.

Design rule: the ML prediction is the *primary* signal, but policy overrides win
when the situation is unambiguous (explicit manual replan, no plan to adjust,
too many micro adjustments). Completion history and free text are NOT overrides:
the feedback service's policy gates whether this graph runs at all. All of it is
pure functions over the state - nothing here reads the database or calls an LLM,
so every branch is trivially testable.

LangGraph conditional edges only call these helpers; they contain no logic of
their own. Adding a route condition means adding it here (see docs/agent/state-machine.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.agent.schemas import RequestIntent
from app.agent.state import PlannerState
from app.ml.base import AdjustmentPrediction, AdjustmentRoute, AdjustmentSeverity

RouteName = Literal["no_change", "micro_adjust", "full_replan"]
RepairRoute = Literal["repair", "continue"]
PreviewRoute = Literal["finalize", "revise"]


@dataclass(slots=True)
class RouteDecision:
    """Result of the routing policy (ML route + any policy override)."""

    route: AdjustmentRoute
    severity: AdjustmentSeverity
    reasons: list[str] = field(default_factory=list)
    overridden: bool = False
    policy_reason: str | None = None
    prediction_source: str = "fallback"


class AdjustmentRouter:
    """Turns an :class:`AdjustmentPrediction` into a final route."""

    def __init__(
        self,
        *,
        low_completion_threshold: float = 0.3,
        max_micro_adjustments: int = 2,
        failure_min_days_elapsed: int = 2,
    ) -> None:
        self.low_completion_threshold = low_completion_threshold
        self.max_micro_adjustments = max_micro_adjustments
        self.failure_min_days_elapsed = failure_min_days_elapsed

    def decide(self, state: PlannerState) -> RouteDecision:
        prediction: AdjustmentPrediction | None = state.get("ml_prediction")
        base = self._base_prediction(prediction)
        reasons = list(base.reasons)
        decision = RouteDecision(
            route=base.route,
            severity=base.severity,
            reasons=reasons,
            prediction_source=base.source,
        )

        # --- policy overrides (deterministic, ML cannot veto them) ---
        override = self._override(state)
        if override is not None:
            route, why = override
            decision.route = route
            decision.overridden = route != base.route
            decision.policy_reason = why
            decision.reasons = reasons + [why]

        # --- portrait model (user_states / MBTI priors) ---
        # It may ESCALATE (never downgrade) the route: the portrait is a
        # cold-start prior plus EWMA observations, so it must not be able to
        # cancel a stronger signal coming from the ML predictor or the policy.
        profile_route = state.get("profile_replan")
        profile_reason = state.get("profile_replan_reason") or "portrait model"
        if profile_route == "full_replan" and decision.route is not AdjustmentRoute.FULL_REPLAN:
            decision.route = AdjustmentRoute.FULL_REPLAN
            decision.overridden = True
            decision.policy_reason = f"portrait model: {profile_reason}"
            decision.reasons = reasons + [decision.policy_reason]
        elif profile_route == "local_repair" and decision.route is AdjustmentRoute.NO_CHANGE:
            decision.route = AdjustmentRoute.MICRO_ADJUST
            decision.overridden = True
            decision.policy_reason = f"portrait model: {profile_reason}"
            decision.reasons = reasons + [decision.policy_reason]
        return decision

    # -- base prediction ---------------------------------------------------
    @staticmethod
    def _base_prediction(
        prediction: AdjustmentPrediction | None,
    ) -> AdjustmentPrediction:
        if prediction is None:
            return AdjustmentPrediction(
                route=AdjustmentRoute.NO_CHANGE,
                severity=AdjustmentSeverity.NONE,
                confidence=0.0,
                reasons=["no ML prediction available"],
                source="fallback:missing",
            )
        return prediction

    # -- overrides ---------------------------------------------------------
    def _override(self, state: PlannerState) -> tuple[AdjustmentRoute, str] | None:
        # 1. Nothing to adjust yet -> rebuild.
        if state.get("current_plan") is None:
            return AdjustmentRoute.FULL_REPLAN, "no current plan version to adjust"

        # 2. An explicit manual replan always wins. A feedback cycle's free text
        #    is context only and must not be treated as an explicit requirement.
        request = state.get("request")
        if request is not None and request.trigger_type is RequestIntent.REPLAN_REQUEST:
            return AdjustmentRoute.FULL_REPLAN, "explicit manual replan requested"

        # 3. Too many consecutive micro adjustments -> escalate.
        #    Completion rate alone is deliberately NOT an override: the feedback
        #    service's pressure/portrait policy decides whether we get here.
        if int(state.get("adjustment_count") or 0) >= self.max_micro_adjustments:
            return (
                AdjustmentRoute.FULL_REPLAN,
                "too many consecutive micro adjustments",
            )
        return None


# ---------------------------------------------------------------------------
# LangGraph conditional-edge helpers
# ---------------------------------------------------------------------------
def route_after_adjustment(state: PlannerState) -> RouteName:
    """Edge out of ``adjustment_router`` in the feedback loop graph."""
    route = state.get("route") or AdjustmentRoute.NO_CHANGE
    return {
        AdjustmentRoute.NO_CHANGE: "no_change",
        AdjustmentRoute.MICRO_ADJUST: "micro_adjust",
        AdjustmentRoute.FULL_REPLAN: "full_replan",
    }[route]


def should_repair(state: PlannerState) -> RepairRoute:
    """Edge out of ``rule_validation``: repair only while violations remain."""
    violations = state.get("rule_violations") or []
    attempts = int(state.get("repair_attempts") or 0)
    max_attempts = int(state.get("max_repair_attempts") or 2)
    if violations and attempts < max_attempts:
        return "repair"
    return "continue"


def route_after_preview(state: PlannerState) -> PreviewRoute:
    """Edge out of the preview node: confirm -> finalise, adjust -> revise."""
    if state.get("user_adjustment"):
        return "revise"
    return "finalize"


class ClassifyPolicy:
    """Deterministic request classifier (no LLM in the first version)."""

    @staticmethod
    def classify(state: PlannerState) -> tuple[RequestIntent, float, list[str]]:
        request = state.get("request")
        if request is None:
            return RequestIntent.INITIAL_PLAN, 0.3, ["no request on state"]

        reasons: list[str] = []
        if request.plan_id is None:
            reasons.append("no plan_id supplied")
            return RequestIntent.INITIAL_PLAN, 0.9, reasons

        if request.user_note:
            reasons.append("user supplied free-text change request")
            return RequestIntent.USER_ADJUSTMENT, 0.7, reasons

        if request.trigger_type is RequestIntent.FEEDBACK_DRIVEN:
            reasons.append("triggered by the feedback cycle")
            return RequestIntent.FEEDBACK_DRIVEN, 0.8, reasons

        reasons.append("existing plan supplied")
        return RequestIntent.REPLAN_REQUEST, 0.6, reasons


__all__ = [
    "AdjustmentRouter",
    "ClassifyPolicy",
    "PreviewRoute",
    "RepairRoute",
    "RouteDecision",
    "RouteName",
    "route_after_adjustment",
    "route_after_preview",
    "should_repair",
]
