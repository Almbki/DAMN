"""Task persistence."""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select

from app.domain.models import Task
from app.infrastructure.database.models.task import Task as TaskORM
from app.infrastructure.database.repositories.base import RepositoryBase


class TaskRepository(RepositoryBase):
    def create_many(self, tasks: list[Task]) -> list[Task]:
        orms = [
            TaskORM(
                plan_id=t.plan_id,
                goal_id=t.goal_id,
                parent_task_id=t.parent_task_id,
                title=t.title,
                description=t.description,
                estimated_duration=t.estimated_duration,
                predicted_duration=t.predicted_duration,
                cognitive_load=t.cognitive_load,
                priority=t.priority,
                scheduled_date=t.scheduled_date,
                start_time=t.start_time,
                end_time=t.end_time,
                status=t.status,
                completion_probability=t.completion_probability,
                is_flexible=t.is_flexible,
                order_index=t.order_index,
            )
            for t in tasks
        ]
        self._session.add_all(orms)
        self._session.flush()
        for orm in orms:
            self._session.refresh(orm)
        return [Task.model_validate(orm) for orm in orms]

    def get_by_id(self, task_id: int) -> Task | None:
        orm = self._session.get(TaskORM, task_id)
        return Task.model_validate(orm) if orm is not None else None

    def list_by_plan(self, plan_id: int) -> list[Task]:
        stmt = (
            select(TaskORM)
            .where(TaskORM.plan_id == plan_id)
            .order_by(TaskORM.order_index, TaskORM.scheduled_date, TaskORM.id)
        )
        return [Task.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_plan_and_date(self, plan_id: int, day: date) -> list[Task]:
        stmt = (
            select(TaskORM)
            .where(TaskORM.plan_id == plan_id, TaskORM.scheduled_date == day)
            .order_by(TaskORM.order_index, TaskORM.start_time, TaskORM.id)
        )
        return [Task.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def update_fields(self, task_id: int, **fields: object) -> Task | None:
        orm = self._session.get(TaskORM, task_id)
        if orm is None:
            return None
        for field, value in fields.items():
            setattr(orm, field, value)
        self._session.flush()
        return Task.model_validate(orm)

    def list_by_goal(self, goal_id: int) -> list[Task]:
        """Tasks that reference a goal (used to protect goal deletion)."""
        stmt = select(TaskORM).where(TaskORM.goal_id == goal_id).order_by(TaskORM.id)
        return [Task.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def delete_by_plan(self, plan_id: int) -> int:
        """Delete every task of a plan; returns the number of deleted rows.

        Callers must remove dependent rows (task_standards, task_executions)
        first, or let the DB-side FK policy handle them.
        """
        self._session.flush()  # flush pending writes before the bulk delete
        result = self._session.execute(delete(TaskORM).where(TaskORM.plan_id == plan_id))
        return result.rowcount or 0