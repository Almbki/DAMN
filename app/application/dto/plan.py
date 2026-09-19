"""Plan-related application DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.models import Goal, Plan, Task, TaskStandard


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
