"""``load_context`` node (the graph's CONTEXT_BUILD step).

Delegates to the application-layer :class:`ContextBuilderProtocol`. This node is
the only place where the agent obtains user history, and it still performs no
database access itself.
"""

from __future__ import annotations

from app.agent.context import PlanningContext
from app.agent.nodes._shared import get_context
from app.agent.schemas import AgentError
from app.agent.state import PlannerState

NODE = "load_context"


def load_context_node(state: PlannerState, runtime: object) -> dict:
    """Assemble the planning context (memory + progress + current plan)."""
    ctx = get_context(runtime)
    request = state["request"]
    ctx.publish("node.started", {"node": NODE})

    updates: dict = {}
    errors: list[AgentError] = []

    if ctx.context_builder is None:
        planning = PlanningContext(user_id=request.user_id)
        errors.append(
            AgentError(
                node=NODE,
                kind="no_context_builder",
                message="no ContextBuilder injected; running with an empty context",
                recovered=True,
            )
        )
    else:
        try:
            planning = ctx.context_builder.build(
                request.user_id,
                plan_id=request.plan_id,
                user_note=request.user_note,
                profile_overrides=request.profile or None,
            )
        except Exception as exc:  # noqa: BLE001 - context failures must degrade, not crash
            planning = PlanningContext(user_id=request.user_id)
            errors.append(
                AgentError(
                    node=NODE,
                    kind="context_build_failed",
                    message=f"{type(exc).__name__}: {exc}",
                    recovered=True,
                )
            )

    updates["user_context"] = planning
    updates["current_plan"] = planning.current_plan
    updates["progress"] = planning.progress
    updates["user_id"] = request.user_id
    if not state.get("goals") and request.goals:
        updates["goals"] = list(request.goals)
    if errors:
        updates["errors"] = errors
    updates["notes"] = [
        f"load_context: plan={planning.current_plan.plan_id if planning.current_plan else 'none'}, "
        f"memory={len(planning.all_memory())} item(s), "
        f"feedback={len(planning.recent_feedback)}"
    ]
    ctx.publish("node.completed", {"node": NODE, "summary": updates["notes"][0]})
    return updates


__all__ = ["NODE", "load_context_node"]
