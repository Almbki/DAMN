"""``micro_adjustment`` node - lighten the current plan WITHOUT calling an LLM.

Deterministic path for ``MICRO_ADJUST``: reuse the plan's unfinished tasks as
the next draft, scale the daily limits by the factor the predictor suggested,
and let the scheduler + rule engine re-place them. No language model involved.
"""

from __future__ import annotations

from app.agent.goal_identity import goal_index_for_ref
from app.agent.nodes._shared import get_context
from app.agent.schemas import GeneratedTaskDraft, PlanGenerationResult
from app.agent.state import PlannerState, ToolCallRecord
from app.domain.models.enums import Priority

NODE = "micro_adjustment"
#: Clamp on the predictor-suggested reduction so we never produce an empty plan.
MIN_LIMIT_FACTOR = 0.5
MAX_LIMIT_FACTOR = 1.0


def _drafts_from_plan(state: PlannerState) -> list[GeneratedTaskDraft]:
    """Unfinished tasks of the current plan become the next draft set."""
    plan = state.get("current_plan")
    if plan is None:
        return []
    drafts: list[GeneratedTaskDraft] = []
    goals = list(state.get("goals") or [])
    for task in plan.pending_tasks():
        drafts.append(
            GeneratedTaskDraft(
                title=task.title,
                # The persisted task carries a real goal id; drafts use the
                # request-local 1-based index. Convert instead of mixing the
                # two identities in one field.
                goal_id=goal_index_for_ref(task.goal_id, goals),
                estimated_duration=max(task.estimated_duration, 1),
                predicted_duration=task.predicted_duration,
                # Carried tasks were produced by the deterministic estimator;
                # keep the provenance truthful through the micro-adjust path.
                prediction_source="deterministic:workload_estimate",
                cognitive_load=task.cognitive_load,
                priority=task.priority if isinstance(task.priority, Priority) else Priority.MEDIUM,
                subject=task.subject,
                order_index=len(drafts),
                is_flexible=task.is_flexible,
                task_kind=task.task_kind,
                series_id=task.series_id,
                series_index=task.series_index,
                occurrence_date=task.occurrence_date,
                target_amount=task.target_amount,
                target_unit=task.target_unit,
            )
        )
    return drafts


def micro_adjustment_node(state: PlannerState, runtime: object) -> dict:
    """Trim the daily load deterministically and hand off to rule validation."""
    ctx = get_context(runtime)
    ctx.publish("node.started", {"node": NODE})

    prediction = state.get("adjustment")
    suggested = 0.85
    if prediction is not None:
        suggested = float(
            prediction.predicted_parameters.get("suggested_daily_limit_factor", 0.85)
        )
    factor = min(MAX_LIMIT_FACTOR, max(MIN_LIMIT_FACTOR, suggested))

    drafts = _drafts_from_plan(state)
    base = state.get("plan_draft")
    plan_draft = (
        base.model_copy(update={"tasks": drafts})
        if base is not None
        else PlanGenerationResult(tasks=drafts, title="Adjusted plan")
    )

    notes = [
        f"micro_adjustment: {len(drafts)} unfinished task(s), limit_factor={factor:.2f}"
    ]
    ctx.publish("node.completed", {"node": NODE, "summary": notes[0]})
    return {
        "plan_draft": plan_draft,
        "limit_factor": factor,
        "replan_reason": "micro_adjust",
        "repair_attempts": 0,
        "tool_results": [
            ToolCallRecord(
                tool="micro_adjustment",
                ok=True,
                summary=f"limit_factor={factor:.2f}, tasks={len(drafts)}",
            )
        ],
        "notes": notes,
    }


__all__ = ["MAX_LIMIT_FACTOR", "MIN_LIMIT_FACTOR", "NODE", "micro_adjustment_node"]
