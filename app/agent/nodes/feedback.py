"""``process_feedback`` node - turn a saved feedback cycle into planner input.

The ``Feedback`` row is already persisted by ``FeedbackService`` before the graph
runs; this node only interprets the cycle (note, replan reason) and records it.
"""

from __future__ import annotations

from app.agent.nodes._shared import get_context
from app.agent.state import PlannerState

NODE = "process_feedback"


def process_feedback_node(state: PlannerState, runtime: object) -> dict:
    """Record the feedback cycle and derive the replan reason."""
    ctx = get_context(runtime)
    ctx.publish("node.started", {"node": NODE})

    request = state["request"]
    context = state.get("user_context")
    note = (request.user_note or "").strip()

    updates: dict = {}
    if note:
        updates["replan_reason"] = f"user feedback: {note}"
        updates["user_adjustment"] = note

    recent = context.recent_feedback if context is not None else []
    summary = f"{len(recent)} recent check-in(s)"
    if recent:
        latest = recent[-1]
        summary += f", latest completion={latest.completion_rate:.0%}"
        if latest.delay_reason:
            summary += f", reason='{latest.delay_reason}'"

    updates["notes"] = [f"process_feedback: {summary}"]
    ctx.publish("node.completed", {"node": NODE, "summary": summary})
    return updates


__all__ = ["NODE", "process_feedback_node"]
