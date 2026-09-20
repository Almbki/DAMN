"""TaskStandard persistence (quantifiable "definition of done" items)."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import TaskStandard
from app.infrastructure.database.models.task import Task as TaskORM
from app.infrastructure.database.models.task_standard import TaskStandard as TaskStandardORM
from app.infrastructure.database.repositories.base import RepositoryBase


class TaskStandardRepository(RepositoryBase):
    def create_many(self, standards: list[TaskStandard]) -> list[TaskStandard]:
        orms = [
            TaskStandardORM(
                task_id=s.task_id,
                description=s.description,
                estimated_duration=s.estimated_duration,
                completed=s.completed,
                order_index=s.order_index,
            )
            for s in standards
        ]
        self._session.add_all(orms)
        self._session.flush()
        for orm in orms:
            self._session.refresh(orm)
        return [TaskStandard.model_validate(orm) for orm in orms]

    def list_by_task(self, task_id: int) -> list[TaskStandard]:
        stmt = (
            select(TaskStandardORM)
            .where(TaskStandardORM.task_id == task_id)
            .order_by(TaskStandardORM.order_index, TaskStandardORM.id)
        )
        return [TaskStandard.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_plan(self, plan_id: int) -> list[TaskStandard]:
        stmt = (
            select(TaskStandardORM)
            .join(TaskORM, TaskStandardORM.task_id == TaskORM.id)
            .where(TaskORM.plan_id == plan_id)
            .order_by(TaskStandardORM.task_id, TaskStandardORM.order_index, TaskStandardORM.id)
        )
        return [TaskStandard.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def update_fields(self, standard_id: int, **fields: object) -> TaskStandard | None:
        orm = self._session.get(TaskStandardORM, standard_id)
        if orm is None:
            return None
        for field, value in fields.items():
            setattr(orm, field, value)
        self._session.flush()
        return TaskStandard.model_validate(orm)