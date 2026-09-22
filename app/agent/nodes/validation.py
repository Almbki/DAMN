"""``rule_validation`` node - schedule the drafts and validate hard constraints.

Deterministic: the Scheduler places, the Rule Engine decides. The LLM has no
say here, and this node is the only place a candidate schedule is produced.
"""

from __future__ import annotations

from app.agent.nodes._shared import build_rule_context, current_drafts, drafts_to_tasks, get_context
from app.agent.schemas import RuleValidationResult
from app.agent.state import PlannerState, ToolCallRecord
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
    tasks = drafts_to_tasks(drafts, goal_id_map=state.get("goal_id_map") or {})

    schedule_outcome = ctx.tool(SCHEDULE_TOOL).invoke(
        ScheduleGeneratorInput(tasks=tasks, context=context)
    )
    schedule = schedule_outcome.value
    if schedule is None:  # pragma: no cover - scheduler is pure and deterministic
        raise RuntimeError(f"schedule_generator failed: {schedule_outcome.error}")

    validate_outcome = ctx.tool(VALIDATE_TOOL).invoke(
        RuleValidatorInput(schedule=schedule, context=context)
    )
    validation = validate_outcome.value or RuleValidationResult(passed=True, violations=[])

    ctx.publish("tool.completed", {"tool": SCHEDULE_TOOL, "ok": schedule_outcome.ok})
    ctx.publish("tool.completed", {"tool": VALIDATE_TOOL, "ok": validate_outcome.ok})

    return {
        "candidate_plan": schedule,
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
