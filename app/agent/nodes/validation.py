"""``rule_validation`` node - schedule the drafts and validate hard constraints.

Deterministic: the Scheduler places, the Rule Engine decides. The LLM has no
say here, and this node is the only place a candidate schedule is produced.
"""

from __future__ import annotations

from app.agent.nodes._shared import build_rule_context, current_drafts, drafts_to_tasks, get_context
from app.agent.schemas import RuleValidationResult
from app.agent.state import PlannerState, ToolCallRecord
from app.agent.tools.execution_chunker import chunk_long_drafts, chunk_unscheduled_drafts
from app.agent.tools.rule_validator import RuleValidatorInput
from app.agent.tools.schedule_generator import ScheduleGeneratorInput

NODE = "rule_validation"
SCHEDULE_TOOL = "schedule_generator"
VALIDATE_TOOL = "rule_validator"


def rule_validation_node(state: PlannerState, runtime: object) -> dict:
    """Place the drafts on the calendar and run the hard-constraint engine."""
    ctx = get_context(runtime)
    ctx.publish("node.started", {"node": NODE})

    drafts = current_drafts(state)
    context = build_rule_context(state, drafts)
    # Chunk long work units *before* the first schedule attempt. A 300-minute
    # project unit must not be parked as a single five-hour block on the only
    # day that later happens to have enough contiguous capacity.
    chunked_plan_draft = None
    proactive = chunk_long_drafts(
        drafts,
        daily_limit_minutes=context.daily_limit_minutes,
        available_minutes_per_day=context.available_minutes_per_day,
        max_per_goal_minutes=context.max_daily_minutes_per_goal,
    )
    if proactive is not None:
        drafts = proactive
        plan_draft = state.get("plan_draft")
        if plan_draft is not None:
            chunked_plan_draft = plan_draft.model_copy(update={"tasks": drafts})
            state = {**state, "plan_draft": chunked_plan_draft}
        context = build_rule_context(state, drafts)
    tasks = drafts_to_tasks(drafts, goal_id_map=state.get("goal_id_map") or {})

    schedule_outcome = ctx.tool(SCHEDULE_TOOL).invoke(
        ScheduleGeneratorInput(tasks=tasks, context=context)
    )
    schedule = schedule_outcome.value
    if schedule is None:  # pragma: no cover - scheduler is pure and deterministic
        raise RuntimeError(f"schedule_generator failed: {schedule_outcome.error}")

    # Bounded scheduler-aware fallback: if a draft is still unscheduled after
    # proactive chunking, split long tasks using the scheduler's real free
    # windows. At most 3 attempts; recurring occurrences and already-chunked
    # drafts are never re-chunked.
    for _attempt in range(3):
        if not schedule.unscheduled_task_ids:
            break
        chunkable = {
            task_id
            for task_id in schedule.unscheduled_task_ids
            if getattr(
                schedule.unscheduled_reasons.get(task_id), "code", "UNKNOWN"
            )
            != "HIGH_COGNITIVE_LIMIT"
        }
        if not chunkable:
            break
        tasks_by_id = {
            task.id: task for task in tasks if task.id is not None
        }
        max_block_by_id = {
            task_id: ctx.scheduler.max_contiguous_minutes(
                tasks_by_id[task_id], context, schedule
            )
            for task_id in chunkable
            if task_id in tasks_by_id
        }
        chunked = chunk_unscheduled_drafts(
            drafts,
            chunkable,
            daily_limit_minutes=context.daily_limit_minutes,
            max_block_by_id=max_block_by_id,
        )
        if chunked is None:
            break
        drafts = chunked
        plan_draft = state.get("plan_draft")
        if plan_draft is not None:
            chunked_plan_draft = plan_draft.model_copy(update={"tasks": drafts})
            state = {**state, "plan_draft": chunked_plan_draft}
        context = build_rule_context(state, drafts)
        tasks = drafts_to_tasks(
            drafts, goal_id_map=state.get("goal_id_map") or {}
        )
        schedule_outcome = ctx.tool(SCHEDULE_TOOL).invoke(
            ScheduleGeneratorInput(tasks=tasks, context=context)
        )
        schedule = schedule_outcome.value
        if schedule is None:  # pragma: no cover
            raise RuntimeError(
                f"schedule_generator failed: {schedule_outcome.error}"
            )

    validate_outcome = ctx.tool(VALIDATE_TOOL).invoke(
        RuleValidatorInput(schedule=schedule, context=context)
    )
    validation = validate_outcome.value or RuleValidationResult(passed=True, violations=[])

    ctx.publish("tool.completed", {"tool": SCHEDULE_TOOL, "ok": schedule_outcome.ok})
    ctx.publish("tool.completed", {"tool": VALIDATE_TOOL, "ok": validate_outcome.ok})
    ctx.publish(
        "node.completed",
        {
            "node": NODE,
            "summary": (
                f"{len(validation.violations)} hard violation(s), "
                f"{len(schedule.unscheduled_task_ids)} unscheduled"
            ),
        },
    )

    return {
        "candidate_plan": schedule,
        **({"plan_draft": chunked_plan_draft} if chunked_plan_draft is not None else {}),
        "rule_violations": list(validation.violations),
        "rule_validation": validation,
        "tool_results": [
            ToolCallRecord(
                tool=SCHEDULE_TOOL,
                ok=schedule_outcome.ok,
                duration_ms=schedule_outcome.duration_ms,
                summary=schedule_outcome.summary,
            ),
            ToolCallRecord(
                tool=VALIDATE_TOOL,
                ok=validate_outcome.ok,
                duration_ms=validate_outcome.duration_ms,
                summary=validate_outcome.summary,
            ),
        ],
        "notes": [
            f"rule_validation: {len(validation.violations)} hard violation(s), "
            f"{len(schedule.unscheduled_task_ids)} unscheduled"
        ],
    }


__all__ = ["NODE", "SCHEDULE_TOOL", "VALIDATE_TOOL", "rule_validation_node"]
