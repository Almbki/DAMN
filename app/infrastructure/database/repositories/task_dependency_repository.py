"""TaskDependency persistence (prerequisite edges between tasks)."""

from __future__ import annotations

from sqlalchemy import delete, or_, select

from app.domain.models import TaskDependency
from app.infrastructure.database.models.task import Task as TaskORM
from app.infrastructure.database.models.task_dependency import TaskDependency as TaskDependencyORM
from app.infrastructure.database.repositories.base import RepositoryBase


class TaskDependencyRepository(RepositoryBase):
    def create_many(self, dependencies: list[TaskDependency]) -> list[TaskDependency]:
        orms = [
            TaskDependencyORM(
                task_id=dependency.task_id,
                depends_on_task_id=dependency.depends_on_task_id,
                dependency_type=dependency.dependency_type,
                created_at=dependency.created_at,
            )
            for dependency in dependencies
        ]
        self._session.add_all(orms)
        self._session.flush()
        for orm in orms:
            self._session.refresh(orm)
        return [TaskDependency.model_validate(orm) for orm in orms]

    def list_by_plan(self, plan_id: int) -> list[TaskDependency]:
        stmt = (
            select(TaskDependencyORM)
            .join(TaskORM, TaskDependencyORM.task_id == TaskORM.id)
            .where(TaskORM.plan_id == plan_id)
            .order_by(TaskDependencyORM.id)
        )
        return [TaskDependency.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_task(self, task_id: int) -> list[TaskDependency]:
        """Edges where the task is either the dependent or the prerequisite."""
        stmt = (
            select(TaskDependencyORM)
            .where(
                or_(
                    TaskDependencyORM.task_id == task_id,
                    TaskDependencyORM.depends_on_task_id == task_id,
                )
            )
            .order_by(TaskDependencyORM.id)
        )
        return [TaskDependency.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def delete_by_task(self, task_id: int) -> int:
        result = self._session.execute(
            delete(TaskDependencyORM).where(
                or_(
                    TaskDependencyORM.task_id == task_id,
                    TaskDependencyORM.depends_on_task_id == task_id,
                )
            )
        )
        return result.rowcount or 0


__all__ = ["TaskDependencyRepository"]
