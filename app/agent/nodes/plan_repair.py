"""``plan_repair`` node: bounded, deterministic repair of invalid schedules.

The repair agent never makes a hard-constraint decision - it only proposes
fewer / re-ordered drafts and lets the Rule Engine re-validate them. All ids
follow the PROVISIONAL TASK ID CONTRACT (``order_index + 1``).
"""

from __future__ import annotations

from app.agent.nodes.plan_generation import drafts_to_tasks
from app.agent.nodes.rule_validation import build_rule_context, current_drafts
from app.agent.schemas import GeneratedTaskDraft, PlanRepairResult, RuleValidationResult
from app.agent.state import PlannerState
from app.domain.rules.base import RuleEngine
from app.domain.scheduling.scheduler import Scheduler

#: Violation codes that mean "the plan asks for more capacity than allowed".
_CAPACITY_CODES = frozenset({"daily_limit", "available_time"})

#: Violation codes resolved by re-ordering (shifting) tasks.
_SHIFT_CODES = frozenset(
    {
        "deadline_exceeded",
        "same_day_conflict",
        "high_cognitive_consecutive",
        "high_cognitive_daily_max",
        "insufficient_buffer",
    }
)


class PlanRepairAgent:
    """Deterministic bounded repair.

    Each round, in order:

    1. **Capacity drop** - while the plan exceeds daily limits / available
       capacity, drop the lowest-priority flexible draft (latest first). This
       frees room for everything else, including deadline-bound tasks.
    2. **Shift** - otherwise move tasks implicated in deadline / same-day /
       high-cognitive / buffer violations earlier in ``order_index`` so the
       scheduler re-places them differently.
    3. **Last resort drop** - when shifting made no progress, drop the least
       valuable implicated draft.

    The plan is re-scheduled and re-validated after every action; the loop
    stops at the first valid schedule or after ``max_steps`` rounds.
    """

    name = "plan-repair-mock-v0"

    def __init__(self, max_steps: int = 10) -> None:
        self.max_steps = max_steps

    def run(self, state: PlannerState) -> PlanRepairResult:
        """Repair the current draft set against the hard-constraint engine."""
        scheduler = state.get("scheduler") or Scheduler()
        rule_engine = state.get("rule_engine") or RuleEngine()
        drafts = [draft.model_copy(deep=True) for draft in current_drafts(state)]
        context = build_rule_context(state, drafts)
        changed: list[int] = []
        notes: list[str] = []
        repaired = False

        for _ in range(self.max_steps):
            tasks = drafts_to_tasks(drafts)
            schedule = scheduler.schedule(tasks, context)
            violations = rule_engine.hard_violations(schedule, context)
            if not violations:
                repaired = True
                break

            problem_ids, capacity_issue = self._classify(violations, schedule.unscheduled_task_ids)
            if capacity_issue:
                victim = self._pick_drop(drafts, problem_ids)
                if victim is None:
                    break
                changed.append(victim.order_index + 1)
                drafts.remove(victim)
                notes.append(
                    f"repair: dropped task #{victim.order_index + 1} ({victim.title}) "
                    "to relieve capacity."
                )
                continue

            shifted = self._shift(drafts, problem_ids)
            if shifted:
                changed.extend(shifted)
                notes.append("repair: re-ordered task(s) to resolve a deadline/conflict violation.")
            else:
                victim = self._pick_drop(drafts, problem_ids)
                if victim is None:
                    break
                changed.append(victim.order_index + 1)
                drafts.remove(victim)
                notes.append(
                    f"repair: dropped task #{victim.order_index + 1} ({victim.title}) "
                    "as a last resort."
                )

        return PlanRepairResult(
            repaired=repaired,
            changed_task_ids=changed,
            tasks=drafts,
            notes=notes,
        )

    @staticmethod
    def _classify(
        violations: list[RuleValidationResult], unscheduled_task_ids: list[int]
    ) -> tuple[set[int], bool]:
        problem_ids: set[int] = set()
        capacity_issue = False
        for violation in violations:
            problem_ids.update(violation.task_ids)
            if violation.code in _CAPACITY_CODES:
                capacity_issue = True
        problem_ids.update(unscheduled_task_ids)
        return problem_ids, capacity_issue

    @staticmethod
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

    @staticmethod
    def _shift(drafts: list[GeneratedTaskDraft], problem_ids: set[int]) -> list[int]:
        """Move implicated tasks earlier in ``order_index``; return changed ids."""
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


def plan_repair_node(state: PlannerState) -> dict:
    """Node function: repair the plan and re-validate it in the same step."""
    attempt = (state.get("repair_attempts") or 0) + 1
    result = PlanRepairAgent().run(state)

    drafts = result.tasks
    tasks = drafts_to_tasks(drafts)
    context = build_rule_context(state, drafts)
    scheduler = state.get("scheduler") or Scheduler()
    rule_engine = state.get("rule_engine") or RuleEngine()
    schedule = scheduler.schedule(tasks, context)
    violations = rule_engine.hard_violations(schedule, context)

    return {
        "repaired_plan": result,
        "final_tasks": list(result.tasks),
        "final_plan": schedule,
        "rule_violations": violations,
        "rule_validation": RuleValidationResult(passed=not violations, violations=violations),
        "repair_attempts": attempt,
        "notes": [
            f"plan_repair: attempt {attempt} - "
            f"{'repaired' if result.repaired else 'unresolved'} "
            f"({len(result.changed_task_ids)} task(s) changed)."
        ],
    }
