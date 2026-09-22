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

    @property
    def plain_tasks(self) -> list[Task]:
        return [item.task for item in self.tasks]


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


def diff_days(old_tasks: list[Task], new_tasks: list[Task]) -> list[PlanChangeDay]:
    """Compare two plan versions and report the change per calendar day.

    Tasks are matched across versions by normalised title - plan versions store
    independent task rows with no cross-version id link, so the title is the only
    stable key. A task counted as `moved` is attributed to its **new** date; a
    `removed` task to its old date. Days with no change are omitted.
    """
    old_by_title = {task.title.strip().lower(): task for task in old_tasks}
    new_by_title = {task.title.strip().lower(): task for task in new_tasks}
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
