"""``theoretical_analysis`` node - theory workload via ``workload_estimator``."""

from __future__ import annotations

from app.agent.nodes._shared import get_context
from app.agent.schemas import AgentError, TheoreticalAnalysisResult
from app.agent.state import PlannerState, ToolCallRecord
from app.agent.tools.workload_estimator import (
    WorkloadEstimatorInput,
    WorkloadEstimatorTool,
)

NODE = "theoretical_analysis"
TOOL = "workload_estimator"


def theoretical_analysis_node(state: PlannerState, runtime: object) -> dict:
    """Estimate the theoretical workload for each goal."""
    ctx = get_context(runtime)
    request = state["request"]
    ctx.publish("node.started", {"node": NODE})

    payload = WorkloadEstimatorInput(
        goals=list(state.get("goals") or request.goals),
        goal_analysis=state.get("goal_analysis"),
        user_profile=dict(request.profile or {}),
    )
    outcome = ctx.tool(TOOL).invoke(payload)
    ctx.publish("tool.completed", {"tool": TOOL, "ok": outcome.ok})

    updates: dict = {}
    errors: list[AgentError] = []
    result: TheoreticalAnalysisResult | None = outcome.value

    if result is None:
        result = WorkloadEstimatorTool(None).run(payload)
        errors.append(
            AgentError(
                node=NODE,
                kind="tool_failed",
                message=outcome.error or "workload_estimator failed",
                recovered=True,
            )
        )

    updates["theoretical_analysis"] = result
    updates["tool_results"] = [
        ToolCallRecord(
            tool=TOOL,
            ok=outcome.ok,
            duration_ms=outcome.duration_ms,
            summary=outcome.summary or f"{result.total_theoretical_minutes} min",
            error=outcome.error,
        )
    ]
    if errors:
        updates["errors"] = errors
    updates["notes"] = [
        f"theoretical_analysis: {len(result.items)} item(s), "
        f"{result.total_theoretical_minutes} min, difficulty={result.overall_difficulty}"
    ]
    ctx.publish("node.completed", {"node": NODE, "summary": updates["notes"][0]})
    return updates


__all__ = ["NODE", "TOOL", "theoretical_analysis_node"]
