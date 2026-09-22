"""``goal_analysis`` node - goals -> objective + subtasks (via ``task_decomposer``)."""

from __future__ import annotations

from app.agent.nodes._shared import get_context
from app.agent.schemas import AgentError, GoalAnalysisResult
from app.agent.state import PlannerState, ToolCallRecord
from app.agent.tools.task_decomposer import TaskDecomposerInput, TaskDecomposerTool

NODE = "goal_analysis"
TOOL = "task_decomposer"


def goal_analysis_node(state: PlannerState, runtime: object) -> dict:
    """Decompose the requested goals and record the tool call."""
    ctx = get_context(runtime)
    request = state["request"]
    ctx.publish("node.started", {"node": NODE})

    payload = TaskDecomposerInput(
        goals=list(state.get("goals") or request.goals),
        user_profile=dict(request.profile or {}),
        mbti=request.mbti,
        execution_weight=request.execution_weight,
    )
    outcome = ctx.tool(TOOL).invoke(payload)
    ctx.publish("tool.completed", {"tool": TOOL, "ok": outcome.ok})

    updates: dict = {}
    errors: list[AgentError] = []
    result: GoalAnalysisResult | None = outcome.value

    if result is None:
        # The tool failed unexpectedly: use the deterministic path so the run continues.
        result = TaskDecomposerTool(None).run(payload)
        errors.append(
            AgentError(
                node=NODE,
                kind="tool_failed",
                message=outcome.error or "task_decomposer failed",
                recovered=True,
            )
        )

    updates["goal_analysis"] = result
    updates["tool_results"] = [
        ToolCallRecord(
            tool=TOOL,
            ok=outcome.ok,
            duration_ms=outcome.duration_ms,
            summary=outcome.summary or f"{len(result.goals)} goal(s)",
            error=outcome.error,
        )
    ]
    if errors:
        updates["errors"] = errors
    updates["notes"] = [
        f"goal_analysis: {len(result.goals)} goal(s), confidence={result.confidence:.2f}"
    ]
    ctx.publish("node.completed", {"node": NODE, "summary": updates["notes"][0]})
    return updates


__all__ = ["NODE", "TOOL", "goal_analysis_node"]
