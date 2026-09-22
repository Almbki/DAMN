"""Adjustment routing policy.

Design rule: the ML prediction is the *primary* signal, but policy overrides win
when the situation is unambiguous (explicit user request, no plan to adjust,
persistently failing plan). All of it is pure functions over the state - nothing
here reads the database or calls an LLM, so every branch is trivially testable.

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
IntentRoute = Literal["initial", "feedback", "replan"]


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

        # 2. An explicit user requirement always wins.
        if (state.get("user_adjustment") or "").strip():
            return AdjustmentRoute.FULL_REPLAN, "user provided an explicit new requirement"

        # 3. Persistently failing plan -> stop micro-adjusting.
        #    Require actual elapsed days: a brand-new plan has completion 0.0 for
        #    trivial reasons and must not be escalated on day one.
        progress = state.get("progress")
        if (
            progress is not None
            and progress.days_elapsed >= self.failure_min_days_elapsed
            and progress.completion_rate < self.low_completion_threshold
        ):
            return (
                AdjustmentRoute.FULL_REPLAN,
                f"completion rate {progress.completion_rate:.2f} is below "
                f"{self.low_completion_threshold:.2f} after "
                f"{progress.days_elapsed} day(s)",
            )

        # 4. Too many consecutive micro adjustments -> escalate.
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


def route_after_classify(state: PlannerState) -> IntentRoute:
    """Edge out of ``classify_request`` (first graph)."""
    intent = state.get("classify")
    if intent is None:
        return "initial"
    if intent.intent in {RequestIntent.ADJUST_PREVIEW, RequestIntent.USER_ADJUSTMENT}:
        return "initial"
    if intent.intent is RequestIntent.FEEDBACK_DRIVEN:
        return "feedback"
    if intent.intent is RequestIntent.REPLAN_REQUEST:
        return "replan"
    return "initial"


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
    "IntentRoute",
    "PreviewRoute",
    "RepairRoute",
    "RouteDecision",
    "RouteName",
    "route_after_adjustment",
    "route_after_classify",
    "route_after_preview",
    "should_repair",
]
