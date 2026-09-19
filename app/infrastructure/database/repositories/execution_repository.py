"""TaskExecution persistence (the ML data asset)."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import TaskExecution
from app.infrastructure.database.models.execution import TaskExecution as TaskExecutionORM
from app.infrastructure.database.repositories.base import RepositoryBase


class TaskExecutionRepository(RepositoryBase):
    def create(self, execution: TaskExecution) -> TaskExecution:
        orm = TaskExecutionORM(
            task_id=execution.task_id,
            user_id=execution.user_id,
            planned_duration=execution.planned_duration,
            actual_duration=execution.actual_duration,
            completion_rate=execution.completion_rate,
            started_at=execution.started_at,
            finished_at=execution.finished_at,
            difficulty_feedback=execution.difficulty_feedback,
            stress_before=execution.stress_before,
            stress_after=execution.stress_after,
            failure_reason=execution.failure_reason,
            time_of_day=execution.time_of_day,
            completed=execution.completed,
            created_at=execution.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return TaskExecution.model_validate(orm)

    def list_by_user(self, user_id: int, limit: int = 500) -> list[TaskExecution]:
        stmt = (
            select(TaskExecutionORM)
            .where(TaskExecutionORM.user_id == user_id)
            .order_by(TaskExecutionORM.created_at.desc(), TaskExecutionORM.id.desc())
            .limit(limit)
        )
        return [TaskExecution.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_task(self, task_id: int) -> list[TaskExecution]:
        stmt = (
            select(TaskExecutionORM)
            .where(TaskExecutionORM.task_id == task_id)
            .order_by(TaskExecutionORM.created_at, TaskExecutionORM.id)
        )
        return [TaskExecution.model_validate(orm) for orm in self._session.scalars(stmt).all()]