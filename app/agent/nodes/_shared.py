"""Shared node helpers.

Kept private (``_shared``) so nodes stay small and the provisional-id contract
lives in exactly one place.
"""

from __future__ import annotations

from datetime import date, time

from app.agent.context import PlanningContext, UserPreferences
from app.agent.schemas import GeneratedTaskDraft
from app.agent.state import PlannerContext, PlannerState
from app.domain.models import Task
from app.domain.models.enums import TaskStatus
from app.domain.rules.base import RuleContext

DEFAULT_CONFLICTING_SUBJECTS: list[tuple[str, str]] = [("math", "algorithm")]
DEFAULT_DAY_START = time(8, 0)
DEFAULT_DAY_END = time(22, 0)


def get_context(runtime: object) -> PlannerContext:
    """Read the injected :class:`PlannerContext` from a LangGraph runtime (or shim)."""
    context = getattr(runtime, "context", None)
    if context is None:
        raise RuntimeError(
            "PlannerContext missing: call the graph with context=PlannerContext(...)"
        )
    return context  # type: ignore[return-value]


def current_drafts(state: PlannerState) -> list[GeneratedTaskDraft]:
    """The active draft set.

    ``plan_draft`` is the single source of truth: when ``plan_repair`` changes the
    drafts it writes them back into ``plan_draft`` (and keeps a
    :class:`PlanRepairResult` record in ``repaired_plan`` for the trace), so a
    later re-draft can never be shadowed by a stale repair.
    """
    plan_draft = state.get("plan_draft")
    if plan_draft is not None and getattr(plan_draft, "tasks", None):
        return list(plan_draft.tasks)
    return []


def drafts_to_tasks(
    drafts: list[GeneratedTaskDraft],
    *,
    plan_id: int = 0,
    goal_id_map: dict[int, int] | None = None,
) -> list[Task]:
    """Convert drafts into schedulable domain tasks.

    PROVISIONAL TASK ID CONTRACT: ``id = order_index + 1`` (1-based). Every node
    that needs to reference a task before persistence uses this mapping; the
    Plan Service remaps to real primary keys after saving.
    """
    goal_id_map = goal_id_map or {}
    tasks: list[Task] = []
    for draft in drafts:
        tasks.append(
            Task(
                id=draft.order_index + 1,
                plan_id=plan_id,
                goal_id=goal_id_map.get(draft.goal_id or 0, draft.goal_id),
                title=draft.title,
                description=draft.description,
                estimated_duration=max(draft.estimated_duration, 1),
                predicted_duration=draft.predicted_duration,
                cognitive_load=draft.cognitive_load,
                priority=draft.priority,
                scheduled_date=None,
                start_time=None,
                end_time=None,
                status=TaskStatus.SCHEDULED,
                completion_probability=draft.completion_probability,
                order_index=draft.order_index,
            )
        )
    return tasks


def resolve_preferences(state: PlannerState) -> UserPreferences:
    """Preferences = stored defaults, then only the client's explicit overrides.

    Layering (highest wins):
    1. ``state["limit_factor"]`` (a MICRO_ADJUST scaling of the final values)
    2. ``request.preferences`` — **only fields that were actually sent**; an
       omitted field keeps the stored value instead of forcing a default
    3. the user's stored preferences (dedicated column, else ``profile``)
    """
    context: PlanningContext | None = state.get("user_context")
    base = context.preferences if context is not None else UserPreferences()

    request = state.get("request")
    override = getattr(request, "preferences", None) if request is not None else None
    resolved = base
    if override is not None:
        updates: dict[str, object] = {}
        for field in (
            "available_minutes_per_day",
            "daily_limit_minutes",
            "buffer_minutes",
            "high_cognitive_max_per_day",
        ):
            value = getattr(override, field, None)
            if value is not None:
                updates[field] = int(value)
        if override.day_start is not None:
            updates["day_start"] = _parse_time(override.day_start, base.day_start)
        if override.day_end is not None:
            updates["day_end"] = _parse_time(override.day_end, base.day_end)
        if override.preferred_time_slots:
            updates["preferred_time_slots"] = dict(override.preferred_time_slots)
        if override.unavailable_weekdays:
            updates["unavailable_weekdays"] = list(override.unavailable_weekdays)
        if updates:
            resolved = resolved.model_copy(update=updates)

    factor = float(state.get("limit_factor") or 1.0)
    if factor != 1.0:
        resolved = resolved.model_copy(
            update={
                "daily_limit_minutes": max(30, int(resolved.daily_limit_minutes * factor)),
                "available_minutes_per_day": max(
                    30, int(resolved.available_minutes_per_day * factor)
                ),
            }
        )
    return resolved


def _parse_time(value: object, default: time) -> time:
    """Accept ``time`` or ``"HH:MM"`` strings from the client."""
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

    Limits come from the resolved preferences; subjects/deadlines are keyed by
    the PROVISIONAL TASK ID CONTRACT; ``completed_task_ids`` comes from the
    current plan snapshot so finished work is never re-scheduled.
    """
    preferences = resolve_preferences(state)
    drafts = drafts if drafts is not None else current_drafts(state)

    task_subjects: dict[int, str] = {}
    task_deadlines: dict[int, date] = {}
    for draft in drafts:
        task_id = draft.order_index + 1  # PROVISIONAL TASK ID CONTRACT
        if draft.subject:
            task_subjects[task_id] = draft.subject
        if draft.deadline is not None:
            task_deadlines[task_id] = draft.deadline.date()

    context: PlanningContext | None = state.get("user_context")
    profile = (context.profile if context is not None else None) or {}
    raw_conflicts = profile.get("conflicting_subject_pairs") or DEFAULT_CONFLICTING_SUBJECTS
    conflicts = [tuple(pair) for pair in raw_conflicts]

    completed: set[int] = set()
    plan = state.get("current_plan")
    if plan is not None:
        completed = {
            task.task_id
            for task in plan.tasks
            if task.status == TaskStatus.COMPLETED
        }

    return RuleContext(
        daily_limit_minutes=preferences.daily_limit_minutes,
        buffer_minutes=preferences.buffer_minutes,
        high_cognitive_max_per_day=preferences.high_cognitive_max_per_day,
        available_minutes_per_day=preferences.available_minutes_per_day,
        day_start=preferences.day_start,
        day_end=preferences.day_end,
        task_subjects=task_subjects,
        task_deadlines=task_deadlines,
        completed_task_ids=completed,
        conflicting_subject_pairs=conflicts,
    )


def preferences_block(state: PlannerState) -> dict:
    """Preferences as a JSON-friendly dict for prompt variables."""
    return resolve_preferences(state).model_dump(mode="json")


#: State keys whose `.confidence` contributes to the run's overall confidence.
_CONFIDENCE_KEYS = (
    "goal_analysis",
    "theoretical_analysis",
    "user_situation",
    "plan_draft",
)


def compute_confidence(state: PlannerState) -> float:
    """Mean confidence of the analysis stages (0.5 when nothing reports one).

    This is the single place the plan confidence is derived; `preview` and
    `plan_finalization` both use it so the number the user sees in the preview is
    exactly the number stored on the plan.
    """
    values: list[float] = []
    for key in _CONFIDENCE_KEYS:
        value = state.get(key)
        confidence = getattr(value, "confidence", None)
        if confidence is not None:
            values.append(float(confidence))
    if not values:
        return 0.5
    return round(sum(values) / len(values), 4)


__all__ = [
    "DEFAULT_CONFLICTING_SUBJECTS",
    "build_rule_context",
    "compute_confidence",
    "current_drafts",
    "drafts_to_tasks",
    "get_context",
    "preferences_block",
    "resolve_preferences",
]
