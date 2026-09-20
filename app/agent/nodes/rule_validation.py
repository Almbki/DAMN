"""``rule_validation`` node: schedule the drafts and validate hard constraints.

The Scheduler produces a candidate schedule and the Rule Engine is the only
authority on whether it satisfies the hard constraints. LangGraph never decides
constraints - it only routes on the violation list produced here.
"""

from __future__ import annotations

from datetime import date, time

from app.agent.nodes.plan_generation import drafts_to_tasks
from app.agent.schemas import GeneratedTaskDraft, RuleValidationResult
from app.agent.state import PlannerState
from app.domain.rules.base import RuleContext, RuleEngine
from app.domain.scheduling.scheduler import Scheduler


def current_drafts(state: PlannerState) -> list[GeneratedTaskDraft]:
    """The active draft set: repaired drafts if any, else the original draft."""
    repaired = state.get("repaired_plan")
    if repaired is not None and getattr(repaired, "tasks", None):
        return list(repaired.tasks)
    plan_draft = state.get("plan_draft")
    if plan_draft is not None and getattr(plan_draft, "tasks", None):
        return list(plan_draft.tasks)
    return []


def _parse_time(value, default: time) -> time:
    """Accept ``time`` or ``"HH:MM"`` strings from the user profile."""
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        try:
            hour, minute = value.strip().split(":", 1)
            return time(int(hour), int(minute))
        except (ValueError, TypeError):
            return default
    return default


def build_rule_context(
    state: PlannerState, drafts: list[GeneratedTaskDraft] | None = None
) -> RuleContext:
    """Build the :class:`RuleContext` for the current draft set.

    Limits come from ``state["request"]``; subjects and deadlines are mapped
    by the PROVISIONAL TASK ID CONTRACT (``order_index + 1``); the user profile
    may override the day window, the conflicting-subject pairs and supply
    completed task ids.
    """
    request = state["request"]
    drafts = drafts if drafts is not None else current_drafts(state)

    task_subjects: dict[int, str] = {}
    task_deadlines: dict[int, date] = {}
    for draft in drafts:
        task_id = draft.order_index + 1  # PROVISIONAL TASK ID CONTRACT
        if draft.subject:
            task_subjects[task_id] = draft.subject
        if draft.deadline is not None:
            task_deadlines[task_id] = draft.deadline.date()

    profile = state.get("user_profile") or {}
    raw_conflicts = profile.get("conflicting_subject_pairs")
    if not isinstance(raw_conflicts, list) or not raw_conflicts:
        raw_conflicts = [("math", "algorithm")]
    conflicts = [tuple(pair) for pair in raw_conflicts]

    raw_completed = profile.get("completed_task_ids")
    completed: set[int] = set()
    if isinstance(raw_completed, (list, set)):
        completed = {int(task_id) for task_id in raw_completed}

    return RuleContext(
        daily_limit_minutes=request.daily_limit_minutes,
        buffer_minutes=request.buffer_minutes,
        high_cognitive_max_per_day=request.high_cognitive_max_per_day,
        available_minutes_per_day=request.available_minutes_per_day,
        day_start=_parse_time(profile.get("day_start"), time(8, 0)),
        day_end=_parse_time(profile.get("day_end"), time(22, 0)),
        task_subjects=task_subjects,
        task_deadlines=task_deadlines,
        completed_task_ids=completed,
        conflicting_subject_pairs=conflicts,
    )


def rule_validation_node(state: PlannerState) -> dict:
    """Node function: schedule the drafts and run the hard-constraint engine."""
    drafts = current_drafts(state)
    tasks = drafts_to_tasks(drafts)
    context = build_rule_context(state, drafts)
    scheduler = state.get("scheduler") or Scheduler()
    rule_engine = state.get("rule_engine") or RuleEngine()

    schedule = scheduler.schedule(tasks, context)
    violations = rule_engine.hard_violations(schedule, context)

    return {
        "candidate_plan": schedule,
        "rule_violations": violations,
        "rule_validation": RuleValidationResult(passed=not violations, violations=violations),
        "notes": [
            f"rule_validation: {len(violations)} hard violation(s), "
            f"{len(schedule.unscheduled_task_ids)} task(s) unscheduled."
        ],
    }
