"""``plan_finalization`` node - freeze the drafts into the final plan payload.

The Service persists this; the node itself only shapes the data.
"""

from __future__ import annotations

from app.agent.nodes._shared import compute_confidence, current_drafts, get_context
from app.agent.schemas import FinalPlanPayload
from app.agent.state import PlannerState
from app.domain.feedback.models import AdjustmentRoute

NODE = "plan_finalization"


def _trigger_source(state: PlannerState) -> str:
    """Explicit workflow metadata -> audit trigger (never guessed from notes)."""
    workflow = str(state.get("workflow") or "")
    if workflow == "manual_replan":
        return "manual_replan"
    if workflow == "feedback_replan":
        if state.get("route") is AdjustmentRoute.MICRO_ADJUST:
            return "micro_adjust"
        return "feedback_full_replan"
    if int(state.get("adjustment_count") or 0) > 0:
        return "preview_adjusted"
    return "initial_plan"


def plan_finalization_node(state: PlannerState, runtime: object) -> dict:
    """Build the final plan payload from the validated drafts."""
    ctx = get_context(runtime)
    ctx.publish("node.started", {"node": NODE})

    drafts = current_drafts(state)
    plan_draft = state.get("plan_draft")
    validation = state.get("rule_validation")
    request = state.get("request")
    # Derived here (not read from the state) so it can never be stale/absent.
    confidence = compute_confidence(state)

    payload = FinalPlanPayload(
        title=(plan_draft.title if plan_draft else "") or "Adaptive Plan",
        start_date=request.start_date if request else None,
        end_date=request.end_date if request else None,
        tasks=drafts,
        confidence=confidence,
        trigger_source=_trigger_source(state),
        rule_violations=list(validation.violations) if validation else [],
    )
    ctx.publish(
        "plan.generated",
        {"tasks": len(drafts), "trigger_source": payload.trigger_source, "node": NODE},
    )
    ctx.publish(
        "node.completed",
        {"node": NODE, "summary": f"{len(drafts)} task(s), confidence={confidence:.2f}"},
    )
    return {
        "final_plan": payload,
        "confidence": confidence,
        "notes": [
            f"plan_finalization: {len(drafts)} task(s), "
            f"trigger={payload.trigger_source}, "
            f"confidence={confidence:.2f}, "
            f"violations={len(payload.rule_violations)}"
        ],
    }


__all__ = ["NODE", "plan_finalization_node"]
