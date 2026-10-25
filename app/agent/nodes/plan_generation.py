"""``plan_generation`` node - drafts for initial plan / preview adjustment / replan."""

from __future__ import annotations

import json

from app.agent.nodes._shared import get_context, resolve_preferences
from app.agent.schemas import AgentError, PlanGenerationResult
from app.agent.state import PlannerState, PreferenceInput, ToolCallRecord
from app.agent.tools.memory_retriever import MemoryQuery, MemoryRetrieverInput
from app.agent.tools.plan_drafter import PlanDrafterInput, PlanDrafterMode, PlanDrafterTool
from app.domain.decomposition.validation import DraftIssue, validate_draft_tasks

NODE = "plan_generation"
TOOL = "plan_drafter"


def _issue_summary(issues: list[DraftIssue], *, limit: int = 5) -> str:
    """Compact, user-facing description of the format issues (bounded length)."""
    rendered = [
        f"{issue.code} at task {issue.task_index}: {issue.message}"
        for issue in issues[:limit]
    ]
    if len(issues) > limit:
        rendered.append(f"... and {len(issues) - limit} more")
    return ", ".join(rendered)


def _goal_count(state: PlannerState) -> int:
    """Number of goals the drafts may reference (goal_id is a 1-based index)."""
    goals = state.get("goals")
    if not goals:
        request = state.get("request")
        goals = request.goals if request is not None else []
    return len(goals)


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
        replan_reason=state.get("replan_reason"),
        completed_task_titles=_completed_titles(state),
        prediction_source=state.get("prediction_source"),
        user_model_context=_user_model_block(state),
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

    # Format gate: detect structurally broken drafts before the scheduler and the
    # preview consume them. A retry is bounded and only happens when the draft is
    # actually invalid, so valid (deterministic) generations are unchanged.
    goal_count = _goal_count(state)
    issues = validate_draft_tasks(result.tasks, goal_count=goal_count)
    format_retries = 0
    max_format_retries = max(0, int(ctx.config.llm_max_retries))
    while issues and format_retries < max_format_retries:
        format_retries += 1
        ctx.publish(
            "draft.format_invalid",
            {
                "node": NODE,
                "attempt": format_retries,
                "max_attempts": max_format_retries,
                "issues": [
                    {
                        "code": issue.code,
                        "message": issue.message,
                        "task_index": issue.task_index,
                    }
                    for issue in issues
                ],
            },
        )
        retry_outcome = ctx.tool(TOOL).invoke(payload)
        ctx.publish("tool.completed", {"tool": TOOL, "ok": retry_outcome.ok})
        if retry_outcome.value is None:
            errors.append(
                AgentError(
                    node=NODE,
                    kind="tool_failed",
                    message=(
                        retry_outcome.error
                        or "plan_drafter failed during format retry"
                    ),
                    recovered=True,
                )
            )
            break
        outcome = retry_outcome
        result = retry_outcome.value
        issues = validate_draft_tasks(result.tasks, goal_count=goal_count)

    if issues:
        # Still return a preview: quality is never a hard gate and the user may
        # fix the draft by adjusting the prompt. The warning is explicit and the
        # errors are part of the run state, so nothing is silently accepted.
        message = (
            f"draft format check failed after {format_retries} retry attempt(s): "
            + _issue_summary(issues)
        )
        errors.append(
            AgentError(
                node=NODE,
                kind="draft_format_invalid",
                message=message,
                recovered=False,
            )
        )
        notes = [f"plan_generation[{mode.value}]: {message}"]
    else:
        retry_note = (
            f" after {format_retries} format retry attempt(s)" if format_retries else ""
        )
        notes = [f"plan_generation[{mode.value}]: {len(result.tasks)} draft(s){retry_note}"]

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
    updates["notes"] = notes
    ctx.publish(
        "node.completed",
        {"node": NODE, "summary": notes[0], "format_retries": format_retries},
    )
    return updates


__all__ = ["NODE", "TOOL", "plan_generation_node"]
