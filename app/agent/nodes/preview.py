"""``preview`` node - pause the graph and wait for the user's decision.

Uses LangGraph's ``interrupt`` so the run is checkpointed mid-flight. The node
enforces the adjustment budget: once ``max_adjustments`` is reached the user is
pushed into execution instead of being allowed to regenerate forever.
"""

from __future__ import annotations

from app.agent.nodes._shared import compute_confidence, current_drafts, get_context
from app.agent.schemas import (
    PreviewDecision,
    PreviewPayload,
    PreviewTask,
)
from app.agent.state import PlannerState

NODE = "preview"


def build_preview_payload(state: PlannerState, max_adjustments: int) -> PreviewPayload:
    """Assemble the preview from the drafts plus their scheduled placement."""
    drafts = current_drafts(state)
    schedule = state.get("candidate_plan")
    placed = {item.task_id: item for item in (schedule.tasks if schedule else [])}
    validation = state.get("rule_validation")

    tasks: list[PreviewTask] = []
    for draft in drafts:
        slot = placed.get(draft.order_index + 1)  # PROVISIONAL TASK ID CONTRACT
        tasks.append(
            PreviewTask(
                order_index=draft.order_index,
                title=draft.title,
                description=draft.description,
                goal_id=draft.goal_id,
                subject=draft.subject,
                cognitive_load=draft.cognitive_load,
                priority=draft.priority,
                estimated_duration=draft.estimated_duration,
                predicted_duration=draft.predicted_duration,
                completion_probability=draft.completion_probability,
                recommended_time_slot=draft.recommended_time_slot,
                standards=list(draft.standards),
                scheduled_date=slot.scheduled_date if slot else None,
                start_time=slot.start_time if slot else None,
                end_time=slot.end_time if slot else None,
            )
        )

    adjustment_count = int(state.get("adjustment_count") or 0)
    request = state.get("request")
    plan_draft = state.get("plan_draft")
    return PreviewPayload(
        thread_id="",
        title=(plan_draft.title if plan_draft else "") or "Adaptive Plan",
        start_date=request.start_date if request else None,
        end_date=request.end_date if request else None,
        tasks=tasks,
        rule_violations=list(validation.violations) if validation else [],
        confidence=compute_confidence(state),
        adjustment_count=adjustment_count,
        max_adjustments=max_adjustments,
        can_adjust=adjustment_count < max_adjustments,
        notes=list(state.get("notes") or [])[-5:],
    )


def preview_node(state: PlannerState, runtime: object) -> dict:
    """Pause for confirm/adjust, enforcing the adjustment budget."""
    from langgraph.types import interrupt

    ctx = get_context(runtime)
    # Publish `started` before the interrupt: once the graph pauses this node
    # never reaches its `completed` publish, and the trace/SSE must still show it.
    ctx.publish("node.started", {"node": NODE})
    max_adjustments = ctx.config.max_preview_adjustments
    payload = build_preview_payload(state, max_adjustments)

    ctx.publish(
        "waiting_user_confirmation",
        {
            "adjustment_count": payload.adjustment_count,
            "max_adjustments": max_adjustments,
            "can_adjust": payload.can_adjust,
            "tasks": len(payload.tasks),
        },
    )
    raw = interrupt(payload.model_dump(mode="json"))
    decision = PreviewDecision.model_validate(raw or {"action": "confirm"})

    updates: dict = {"preview": payload}
    errors = []

    if decision.action == "adjust" and not payload.can_adjust:
        updates["adjustment_rejected"] = True
        updates["user_adjustment"] = None
        updates["notes"] = [
            "preview: adjustment budget exhausted - please start executing the plan"
        ]
    elif decision.action == "adjust" and decision.feedback:
        updates["user_adjustment"] = decision.feedback
        updates["adjustment_count"] = payload.adjustment_count + 1
        updates["adjustment_rejected"] = False
        updates["notes"] = [
            f"preview: adjustment #{payload.adjustment_count + 1} requested"
        ]
    else:
        updates["user_adjustment"] = None
        updates["adjustment_rejected"] = False
        updates["notes"] = ["preview: confirmed by the user"]

    if errors:
        updates["errors"] = errors
    ctx.publish("preview.generated", {"tasks": len(payload.tasks), "node": NODE})
    ctx.publish(
        "node.completed",
        {"node": NODE, "summary": updates["notes"][-1] if updates.get("notes") else ""},
    )
    return updates


__all__ = ["NODE", "build_preview_payload", "preview_node"]
