"""``new_plan`` node - finalise a new plan version after a feedback cycle.

Shared by both the MICRO_ADJUST and FULL_REPLAN branches. It reuses the
finalisation logic (single place that shapes the final payload) and tags the
trigger so the Service can record the right ``ReplanEvent``.
"""

from __future__ import annotations

from app.agent.nodes.finalization import plan_finalization_node
from app.agent.state import PlannerState

NODE = "new_plan"


def new_plan_node(state: PlannerState, runtime: object) -> dict:
    """Produce the final payload for a new plan version."""
    updates = plan_finalization_node(state, runtime)
    updates["notes"] = [
        f"new_plan: version created from the {updates.get('final_plan').trigger_source} route"
    ]
    return updates


__all__ = ["NODE", "new_plan_node"]
