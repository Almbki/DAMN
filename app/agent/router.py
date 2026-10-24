"""Adjustment routing policy.

The route is produced by the *deterministic* domain policy
(:func:`app.domain.feedback.adjustment.decide_adjustment`); this module only
applies unambiguous policy overrides (explicit manual replan, nothing to adjust,
too many consecutive micro adjustments).

There is no ML model here and no LLM call: every branch is a pure function over
the state, so it is trivially testable and cannot override the Rule Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.agent.schemas import RequestIntent
from app.agent.state import PlannerState
from app.domain.feedback.models import (
    AdjustmentDecision,
    AdjustmentRoute,
    AdjustmentSeverity,
)

RouteName = Literal["no_change", "micro_adjust", "full_replan"]
RepairRoute = Literal["repair", "continue"]
PreviewRoute = Literal["finalize", "revise"]


@dataclass(slots=True)
class RouteDecision:
    """Result of the routing policy (base decision + any policy override)."""

    route: AdjustmentRoute
    severity: AdjustmentSeverity
    reasons: list[str] = field(default_factory=list)
    overridden: bool = False
    policy_reason: str | None = None
    prediction_source: str = "policy:deterministic"


class AdjustmentRouter:
    """Turns a deterministic :class:`AdjustmentDecision` into a final route."""

    def __init__(
        self,
        *,
        max_micro_adjustments: int = 2,
    ) -> None:
        self.max_micro_adjustments = max_micro_adjustments

    def decide(self, state: PlannerState) -> RouteDecision:
        base = state.get("adjustment") or AdjustmentDecision()
        reasons = list(base.reasons)
        decision = RouteDecision(
            route=base.route,
            severity=base.severity,
            reasons=reasons,
            prediction_source=base.source,
        )

        override = self._override(state)
        if override is not None:
            route, why = override
            decision.route = route
            decision.overridden = route != base.route
            decision.policy_reason = why
            decision.reasons = reasons + [why]
        return decision

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
    route = state.get("route") or AdjustmentRoute.NO_CHANGE
    return {
        AdjustmentRoute.NO_CHANGE: "no_change",
        AdjustmentRoute.MICRO_ADJUST: "micro_adjust",
        AdjustmentRoute.FULL_REPLAN: "full_replan",
    }[route]


def should_repair(state: PlannerState) -> RepairRoute:
    violations = state.get("rule_violations") or []
    attempts = int(state.get("repair_attempts") or 0)
    max_attempts = int(state.get("max_repair_attempts") or 2)
    if violations and attempts < max_attempts:
        return "repair"
    return "continue"


def route_after_preview(state: PlannerState) -> PreviewRoute:
    if state.get("user_adjustment"):
        return "revise"
    return "finalize"


__all__ = [
    "AdjustmentRouter",
    "PreviewRoute",
    "RepairRoute",
    "RouteDecision",
    "RouteName",
    "route_after_adjustment",
    "route_after_preview",
    "should_repair",
]