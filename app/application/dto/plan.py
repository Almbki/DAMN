"""Plan-related application DTOs."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domain.models import Goal, Plan, Task, TaskStandard
from app.domain.models.enums import ReplanTriggerType


class TaskWithStandards(BaseModel):
    task: Task
    standards: list[TaskStandard] = Field(default_factory=list)


class PlanDetail(BaseModel):
    """Aggregate returned by :meth:`PlanService.get_plan`."""

    plan: Plan
    tasks: list[TaskWithStandards] = Field(default_factory=list)
    goals: list[Goal] = Field(default_factory=list)


class PlanChangeDay(BaseModel):
    """What changed on one calendar day."""

    date: date
    added: int = 0
    moved: int = 0
    removed: int = 0
    summary: str = ""
    task_ids: list[int] = Field(default_factory=list)


class PlanChange(BaseModel):
    """One replan event plus its per-day diff (frontend "计划变更")."""

    id: int
    trigger_type: ReplanTriggerType
    reason: str = ""
    old_version: int
    new_version: int
    created_at: datetime
    days: list[PlanChangeDay] = Field(default_factory=list)


def _task_key(task: Task) -> tuple:
    """Cross-version identity: series occurrence, else normalised title."""
    if task.series_id is not None and task.occurrence_date is not None:
        return ("series", task.series_id, task.occurrence_date)
    return ("title", task.title.strip().lower())


def diff_days(old_tasks: list[Task], new_tasks: list[Task]) -> list[PlanChangeDay]:
    """Compare two plan versions and report the change per calendar day.

    Tasks are matched across versions by ``(series_id, occurrence_date)`` when
    they belong to a split goal, else by normalised title. Plan versions store
    independent task rows with no cross-version id link, so titles alone would
    collide for repeated occurrences of the same series. A task counted as
    `moved` is attributed to its **new** date; a `removed` task to its old date.
    Days with no change are omitted.
    """
    old_by_title = {_task_key(task): task for task in old_tasks}
    new_by_title = {_task_key(task): task for task in new_tasks}
    days: dict[date, PlanChangeDay] = {}

    def bucket(day: date) -> PlanChangeDay:
        return days.setdefault(day, PlanChangeDay(date=day))

    for key, task in new_by_title.items():
        if task.scheduled_date is None:
            continue
        previous = old_by_title.get(key)
        entry = bucket(task.scheduled_date)
        if previous is None:
            entry.added += 1
            if task.id is not None:
                entry.task_ids.append(task.id)
        elif previous.scheduled_date != task.scheduled_date:
            entry.moved += 1
            if task.id is not None:
                entry.task_ids.append(task.id)

    for key, task in old_by_title.items():
        if key in new_by_title or task.scheduled_date is None:
            continue
        entry = bucket(task.scheduled_date)
        entry.removed += 1
        if task.id is not None:
            entry.task_ids.append(task.id)

    for entry in days.values():
        parts = []
        if entry.added:
            parts.append(f"新增 {entry.added} 项")
        if entry.moved:
            parts.append(f"挪期 {entry.moved} 项")
        if entry.removed:
            parts.append(f"删除 {entry.removed} 项")
        entry.summary = "，".join(parts) or "无变化"

    return sorted(days.values(), key=lambda item: item.date)


__all__ = [
    "PlanChange",
    "PlanChangeDay",
    "PlanDetail",
    "TaskWithStandards",
    "diff_days",
]
