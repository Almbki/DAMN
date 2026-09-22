"""``adjustment_router`` node - apply the routing policy to the ML prediction.

The decision itself lives in :class:`app.agent.router.AdjustmentRouter`; this
node only runs it and writes ``route`` onto the state.
"""

from __future__ import annotations

from app.agent.nodes._shared import get_context
from app.agent.router import AdjustmentRouter
from app.agent.state import PlannerState

NODE = "adjustment_router"


def adjustment_router_node(state: PlannerState, runtime: object) -> dict:
    """Decide NO_CHANGE / MICRO_ADJUST / FULL_REPLAN."""
    ctx = get_context(runtime)
    ctx.publish("node.started", {"node": NODE})

    router = AdjustmentRouter(
        low_completion_threshold=ctx.config.low_completion_threshold,
        max_micro_adjustments=ctx.config.max_consecutive_micro_adjustments,
    )
    decision = router.decide(state)

    note = (
        f"adjustment_router: {decision.route.value} "
        f"(source={decision.prediction_source}"
        + (f", override={decision.policy_reason}" if decision.overridden else "")
        + ")"
    )
    ctx.publish(
        "node.completed",
        {"node": NODE, "route": decision.route.value, "overridden": decision.overridden},
    )
    return {
        "route": decision.route,
        "notes": [note, *[f"reason: {reason}" for reason in decision.reasons]],
    }


__all__ = ["NODE", "adjustment_router_node"]
