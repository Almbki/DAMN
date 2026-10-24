"""``adjustment_decision`` node - deterministic feedback routing input.

Replaces the retired mock-ML ``ml_prediction`` node. It consumes observed
check-ins (and the Level 2 state when available) and calls the pure domain
policy in :mod:`app.domain.feedback.adjustment`.
"""

from __future__ import annotations

from app.agent.nodes._shared import get_context
from app.agent.schemas import AgentError
from app.agent.state import PlannerState, ToolCallRecord
from app.domain.feedback.adjustment import decide_adjustment
from app.domain.feedback.models import AdjustmentDecision, AdjustmentRoute, AdjustmentSeverity

NODE = "adjustment_decision"


def _hinted_decision(hint: str) -> AdjustmentDecision | None:
    try:
        route = AdjustmentRoute(hint.strip().upper())
    except ValueError:
        return None
    severity = {
        AdjustmentRoute.NO_CHANGE: AdjustmentSeverity.NONE,
        AdjustmentRoute.MICRO_ADJUST: AdjustmentSeverity.MEDIUM,
        AdjustmentRoute.FULL_REPLAN: AdjustmentSeverity.HIGH,
    }[route]
    return AdjustmentDecision(
        route=route,
        severity=severity,
        confidence=0.8,
        reasons=(f"feedback service policy: {route.value}",),
        source="policy:feedback_service",
    )


def adjustment_decision_node(state: PlannerState, runtime: object) -> dict:
    ctx = get_context(runtime)
    ctx.publish("node.started", {"node": NODE})

    context = state.get("user_context")
    recent = list(context.recent_feedback) if context is not None else []

    request = state.get("request")
    hinted = (
        _hinted_decision(request.feedback_route)
        if request and request.feedback_route
        else None
    )
    if hinted is not None:
        ctx.publish(
            "model_inference",
            {
                "node": NODE,
                "model": "deterministic_policy",
                "source": hinted.source,
                "route": hinted.route.value,
            },
        )
        return {
            "adjustment": hinted,
            "tool_results": [
                ToolCallRecord(
                    tool="adjustment_policy",
                    ok=True,
                    summary=f"route={hinted.route.value}, source={hinted.source}",
                    used_llm=False,
                )
            ],
            "notes": [f"adjustment_decision: {hinted.route.value} (service hint)"],
        }

    if not recent:
        decision = decide_adjustment(completion_rates=[])
        ctx.publish(
            "model_inference",
            {
                "node": NODE,
                "model": "deterministic_policy",
                "source": decision.source,
                "route": decision.route.value,
            },
        )
        return {
            "adjustment": decision,
            "errors": [
                AgentError(
                    node=NODE,
                    kind="no_recent_feedback",
                    message="no recent check-ins; no change is proposed",
                    recovered=True,
                )
            ],
            "notes": [f"adjustment_decision: {decision.route.value} (no data)"],
        }

    model = getattr(context, "user_model", None)
    state_snapshot = model.state if model is not None else None
    decision = decide_adjustment(
        completion_rates=[item.completion_rate for item in recent],
        stress_levels=[item.stress_level for item in recent if item.stress_level is not None],
        energy_levels=[item.energy_level for item in recent if item.energy_level is not None],
        state_fatigue=state_snapshot.fatigue.value if state_snapshot else None,
        state_stress=state_snapshot.stress.value if state_snapshot else None,
        state_self_efficacy=state_snapshot.self_efficacy.value if state_snapshot else None,
    )

    ctx.publish(
        "model_inference",
        {
            "node": NODE,
            "model": "deterministic_policy",
            "source": decision.source,
            "route": decision.route.value,
            "level2_available": state_snapshot is not None,
        },
    )
    return {
        "adjustment": decision,
        "tool_results": [
            ToolCallRecord(
                tool="adjustment_policy",
                ok=True,
                summary=f"route={decision.route.value}, source={decision.source}",
                used_llm=False,
            )
        ],
        "notes": [
            f"adjustment_decision: {decision.route.value} "
            f"(severity={decision.severity.value}, source={decision.source})"
        ],
    }


__all__ = ["NODE", "adjustment_decision_node"]