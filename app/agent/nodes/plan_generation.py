"""``plan_generation`` node - drafts for initial plan / preview adjustment / replan."""

from __future__ import annotations

import json

from app.agent.nodes._shared import get_context, resolve_preferences
from app.agent.schemas import AgentError, PlanGenerationResult
from app.agent.state import PlannerState, PreferenceInput, ToolCallRecord
from app.agent.tools.memory_retriever import MemoryQuery, MemoryRetrieverInput
from app.agent.tools.plan_drafter import PlanDrafterInput, PlanDrafterMode, PlanDrafterTool
from app.domain.models.enums import TaskStatus

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


def _user_model_block(state: PlannerState) -> str:
    """Render the real Level 1/2 snapshot for the prompt.

    ``profile_json`` is excluded: it contains the Level 2 audit payload
    (including reflection evidence) and is not needed for task drafting.
    """
    context = state.get("user_context")
    model = context.user_model if context is not None else None
    if model is None:
        return ""
    payload = model.model_dump(mode="json", exclude={"state": {"profile_json"}})
    if not payload.get("trait") and not payload.get("state"):
        return ""
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return (
        "User model snapshot (Level 1 traits + Level 2 pre-task state). Treat it "
        "as evidence about this user, never as a hard constraint and never "
        "re-estimate its numbers:\n" + rendered
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

    goals = list(state.get("goals") or [])
    goal_id_map = state.get("goal_id_map") or {}
    goals = [
        goal.model_copy(
            update={
                "existing_goal_id": goal.existing_goal_id
                or goal_id_map.get(index + 1)
            }
        )
        for index, goal in enumerate(goals)
    ]
    completed_work_by_unit: dict[str, int] = {}
    total_work_by_unit: dict[str, int] = {}
    current = state.get("current_plan")
    current_plan_payload = (
        current.model_dump(mode="json") if current is not None else {}
    )
    if current is not None:
        for task in current.tasks:
            key = task.work_unit_key
            if not key:
                continue
            total_work_by_unit[key] = (
                total_work_by_unit.get(key, 0) + task.estimated_duration
            )
            if task.status == TaskStatus.COMPLETED:
                completed_work_by_unit[key] = (
                    completed_work_by_unit.get(key, 0) + task.estimated_duration
                )
    completed_work_unit_keys = {
        key
        for key, total in total_work_by_unit.items()
        if completed_work_by_unit.get(key, 0) >= total
    }
    payload = PlanDrafterInput(
        mode=mode,
        title=(
            state["request"].plan_title
            or (preview.title if preview else None)
            or "Adaptive Plan"
        ),
        goals=goals,
        completed_work_by_unit=completed_work_by_unit,
        completed_work_unit_keys=completed_work_unit_keys,
        goal_analysis=state.get("goal_analysis"),
        user_situation=state.get("user_situation"),
        theoretical=theoretical.model_dump(mode="json") if theoretical else {},
        start_date=state["request"].start_date,
        end_date=state["request"].end_date,
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
        adjustment=state.get("adjustment"),
        progress=state.get("progress"),
        current_plan=current_plan_payload,
        replan_reason=state.get("replan_reason"),
        completed_task_titles=_completed_titles(state),
        prediction_source=state.get("prediction_source"),
        user_model_context=_user_model_block(state),
    )

    outcome = ctx.tool(TOOL).invoke(payload)
    ctx.publish("tool.completed", {"tool": TOOL, "ok": outcome.ok})
    # Fail closed: a broken recurrence must never silently degrade into a
    # handful of same-day one-off tasks.
    if not outcome.ok and (outcome.error or "").startswith("RecurrenceError"):
        raise RuntimeError(outcome.error)

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
