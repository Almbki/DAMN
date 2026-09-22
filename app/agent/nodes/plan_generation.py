"""``plan_generation`` node - drafts for initial plan / preview adjustment / replan."""

from __future__ import annotations

import json

from app.agent.nodes._shared import get_context, resolve_preferences
from app.agent.schemas import AgentError, PlanGenerationResult
from app.agent.state import PlannerState, PreferenceInput, ToolCallRecord
from app.agent.tools.memory_retriever import MemoryQuery, MemoryRetrieverInput
from app.agent.tools.plan_drafter import PlanDrafterInput, PlanDrafterMode, PlanDrafterTool

NODE = "plan_generation"
TOOL = "plan_drafter"


def _mode(state: PlannerState) -> PlanDrafterMode:
    if (state.get("user_adjustment") or "").strip():
        return PlanDrafterMode.ADJUSTMENT
    if state.get("replan_reason"):
        return PlanDrafterMode.REPLAN
    return PlanDrafterMode.INITIAL


def _completed_titles(state: PlannerState) -> list[str]:
    plan = state.get("current_plan")
    if plan is None:
        return []
    return [
        task.title
        for task in plan.tasks
        if getattr(task.status, "value", task.status) == "completed"
    ]


def _profile_block(state: PlannerState) -> str:
    """Render the portrait for the prompt (cold-start prior, not a diagnosis)."""
    profile = state.get("profile_prompt") or {}
    if not profile:
        return ""
    rendered = json.dumps(profile, ensure_ascii=False, sort_keys=True)
    return (
        "Cold-start portrait (MBTI-derived prior, NOT a diagnosis; it is "
        "overridden by observed feedback as update_count grows). Use it only to "
        "bias the task mix, never to exclude work:\n" + rendered
    )


def plan_generation_node(state: PlannerState, runtime: object) -> dict:
    """Produce the task drafts for the current mode."""
    ctx = get_context(runtime)
    ctx.publish("node.started", {"node": NODE})
    mode = _mode(state)

    theoretical = state.get("theoretical_analysis")
    preferences = resolve_preferences(state)
    preview = state.get("preview")
    user_context = state.get("user_context")

    context_block = ""
    if user_context is not None:
        digest = ctx.tool("memory_retriever").run(
            MemoryRetrieverInput(context=user_context, query=MemoryQuery(limit=15))
        )
        context_block = digest.as_prompt_block()

    payload = PlanDrafterInput(
        mode=mode,
        title=(
            state["request"].plan_title
            or (preview.title if preview else None)
            or "Adaptive Plan"
        ),
        goals=list(state.get("goals") or []),
        user_situation=state.get("user_situation"),
        theoretical=theoretical.model_dump(mode="json") if theoretical else {},
        preferences=PreferenceInput(
            available_minutes_per_day=preferences.available_minutes_per_day,
            daily_limit_minutes=preferences.daily_limit_minutes,
            buffer_minutes=preferences.buffer_minutes,
            high_cognitive_max_per_day=preferences.high_cognitive_max_per_day,
            day_start=preferences.day_start.strftime("%H:%M"),
            day_end=preferences.day_end.strftime("%H:%M"),
            preferred_time_slots=preferences.preferred_time_slots,
            unavailable_weekdays=preferences.unavailable_weekdays,
        ),
        preview=preview,
        user_adjustment=state.get("user_adjustment"),
        adjustment_count=int(state.get("adjustment_count") or 0),
        planning_context=context_block,
        ml_prediction=state.get("ml_prediction"),
        progress=state.get("progress"),
        replan_reason=state.get("replan_reason"),
        completed_task_titles=_completed_titles(state),
        prediction_source=state.get("prediction_source"),
        profile_context=_profile_block(state),
    )

    outcome = ctx.tool(TOOL).invoke(payload)
    ctx.publish("tool.completed", {"tool": TOOL, "ok": outcome.ok})

    updates: dict = {}
    errors: list[AgentError] = []
    result: PlanGenerationResult | None = outcome.value
    if result is None:
        result = PlanDrafterTool(None).run(payload)
        errors.append(
            AgentError(
                node=NODE,
                kind="tool_failed",
                message=outcome.error or "plan_drafter failed",
                recovered=True,
            )
        )

    updates["plan_draft"] = result
    # A fresh draft resets the repair budget for the new candidate.
    updates["repair_attempts"] = 0
    updates["tool_results"] = [
        ToolCallRecord(
            tool=TOOL,
            ok=outcome.ok,
            duration_ms=outcome.duration_ms,
            summary=f"mode={mode.value}, {len(result.tasks)} draft(s)",
            error=outcome.error,
        )
    ]
    if errors:
        updates["errors"] = errors
    updates["notes"] = [f"plan_generation[{mode.value}]: {len(result.tasks)} draft(s)"]
    ctx.publish("node.completed", {"node": NODE, "summary": updates["notes"][0]})
    return updates


__all__ = ["NODE", "TOOL", "plan_generation_node"]
