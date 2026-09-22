"""``plan_repair`` node - deterministic, bounded repair of an invalid schedule.

Strategy per round (mirrors the hard-constraint codes):

1. **Capacity drop** - while the plan exceeds daily limits, drop the lowest
   priority flexible draft (latest first).
2. **Shift** - otherwise move the implicated tasks earlier in ``order_index``
   so the scheduler re-places them.
3. **Last-resort drop** - when shifting makes no progress, drop the least
   valuable implicated draft.

The Rule Engine is re-run after every action; the loop stops at the first valid
schedule or after the bounded number of steps. The LLM is not involved - it may
only *propose* repairs through the ``repair`` prompt in a later iteration.
"""

from __future__ import annotations

from app.agent.nodes._shared import (
    build_rule_context,
    current_drafts,
    drafts_to_tasks,
    get_context,
)
from app.agent.schemas import (
    AgentError,
    GeneratedTaskDraft,
    PlanGenerationResult,
    PlanRepairResult,
    RuleValidationResult,
)
from app.agent.state import PlannerState
from app.agent.tools.rule_validator import RuleValidatorInput
from app.agent.tools.schedule_generator import ScheduleGeneratorInput

NODE = "plan_repair"

#: Violation codes that mean "the plan asks for more capacity than allowed".
_CAPACITY_CODES = frozenset({"daily_limit", "available_time"})
#: Bounded number of repair actions per attempt.
MAX_STEPS = 10


def plan_repair_node(state: PlannerState, runtime: object) -> dict:
    """Repair the current draft set and re-validate it."""
    ctx = get_context(runtime)
    ctx.publish("node.started", {"node": NODE})

    attempt = int(state.get("repair_attempts") or 0) + 1
    goal_id_map = state.get("goal_id_map") or {}
    drafts = [draft.model_copy(deep=True) for draft in current_drafts(state)]
    changed: list[int] = []
    notes: list[str] = []
    repaired = False

    for _ in range(MAX_STEPS):
        context = build_rule_context(state, drafts)
        tasks = drafts_to_tasks(drafts, goal_id_map=goal_id_map)
        schedule = ctx.scheduler.schedule(tasks, context)
        violations = ctx.rule_engine.hard_violations(schedule, context)
        if not violations:
            repaired = True
            break

        problem_ids = {
            task_id for violation in violations for task_id in violation.task_ids
        } | set(schedule.unscheduled_task_ids)
        capacity_issue = any(v.code in _CAPACITY_CODES for v in violations)

        if capacity_issue:
            victim = _pick_drop(drafts, problem_ids)
            if victim is None:
                break
            changed.append(victim.order_index + 1)
            drafts.remove(victim)
            notes.append(f"repair: dropped '{victim.title}' to relieve capacity")
            continue

        shifted = _shift(drafts, problem_ids)
        if shifted:
            changed.extend(shifted)
            notes.append("repair: re-ordered task(s) to resolve a scheduling conflict")
            continue

        victim = _pick_drop(drafts, problem_ids)
        if victim is None:
            break
        changed.append(victim.order_index + 1)
        drafts.remove(victim)
        notes.append(f"repair: dropped '{victim.title}' as a last resort")

    # Re-schedule + re-validate the final draft set.
    context = build_rule_context(state, drafts)
    tasks = drafts_to_tasks(drafts, goal_id_map=goal_id_map)
    schedule_outcome = ctx.tool("schedule_generator").invoke(
        ScheduleGeneratorInput(tasks=tasks, context=context)
    )
    schedule = schedule_outcome.value
    if schedule is None:  # pragma: no cover - scheduler is pure
        raise RuntimeError(f"schedule_generator failed: {schedule_outcome.error}")
    validation_outcome = ctx.tool("rule_validator").invoke(
        RuleValidatorInput(schedule=schedule, context=context)
    )
    validation = validation_outcome.value or RuleValidationResult(passed=True, violations=[])

    base_draft = state.get("plan_draft")
    plan_draft = (
        base_draft.model_copy(update={"tasks": drafts})
        if base_draft is not None
        else PlanGenerationResult(tasks=drafts)
    )
    ctx.publish(
        "node.completed",
        {"node": NODE, "summary": f"attempt {attempt}, valid={validation.passed}"},
    )

    updates: dict = {
        "plan_draft": plan_draft,
        "repaired_plan": PlanRepairResult(
            repaired=repaired,
            changed_task_ids=changed,
            tasks=drafts,
            notes=notes,
        ),
        "candidate_plan": schedule,
        "rule_violations": list(validation.violations),
        "rule_validation": validation,
        "repair_attempts": attempt,
        "notes": [
            f"plan_repair: attempt {attempt} - "
            f"{'valid' if validation.passed else 'still invalid'} "
            f"({len(changed)} task(s) changed)"
        ],
    }
    if not validation.passed and attempt >= int(state.get("max_repair_attempts") or 2):
        updates["errors"] = [
            AgentError(
                node=NODE,
                kind="repair_exhausted",
                message="hard-constraint repair budget exhausted; returning best effort",
                recovered=False,
            )
        ]
    return updates


def _pick_drop(
    drafts: list[GeneratedTaskDraft], problem_ids: set[int]
) -> GeneratedTaskDraft | None:
    """Least valuable draft: implicated first, then lowest priority, then latest."""
    if not drafts:
        return None

    def key(draft: GeneratedTaskDraft) -> tuple[bool, int, int]:
        return (
            (draft.order_index + 1) not in problem_ids,
            int(draft.priority),
            -draft.order_index,
        )

    return sorted(drafts, key=key)[0]


def _shift(drafts: list[GeneratedTaskDraft], problem_ids: set[int]) -> list[int]:
    """Move implicated tasks earlier in ``order_index``; return the changed ids."""
    if not problem_ids:
        return []
    stable = sorted(drafts, key=lambda draft: draft.order_index)
    problematic = [d for d in stable if (d.order_index + 1) in problem_ids]
    if not problematic:
        return []
    reordered = problematic + [d for d in stable if (d.order_index + 1) not in problem_ids]
    changed: list[int] = []
    for new_index, draft in enumerate(reordered):
        if draft.order_index != new_index:
            changed.append(draft.order_index + 1)
        draft.order_index = new_index
    drafts[:] = reordered
    return changed


__all__ = ["MAX_STEPS", "NODE", "plan_repair_node"]
