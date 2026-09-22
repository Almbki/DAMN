"""``classify_request`` node - deterministic intent classification.

No LLM: the first version classifies from the request shape alone
(``ClassifyPolicy``). Swap in a model later without touching the graph.
"""

from __future__ import annotations

from app.agent.nodes._shared import get_context
from app.agent.router import ClassifyPolicy
from app.agent.schemas import ClassifyResult
from app.agent.state import PlannerState

NODE = "classify_request"


def classify_request_node(state: PlannerState, runtime: object) -> dict:
    """Classify what the caller is asking for and record it on the state."""
    ctx = get_context(runtime)
    ctx.publish("node.started", {"node": NODE})

    intent, confidence, reasons = ClassifyPolicy.classify(state)
    result = ClassifyResult(intent=intent, confidence=confidence, reasons=reasons)
    ctx.publish(
        "node.completed", {"node": NODE, "summary": f"intent={intent.value}"}
    )
    return {
        "classify": result,
        "notes": [f"classify_request: {intent.value} (confidence {confidence:.2f})"],
    }


__all__ = ["NODE", "classify_request_node"]
