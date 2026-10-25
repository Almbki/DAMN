"""TaskEvent persistence (append-only task change log)."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import TaskEvent
from app.infrastructure.database.models.task_event import TaskEvent as TaskEventORM
from app.infrastructure.database.repositories.base import RepositoryBase


class TaskEventRepository(RepositoryBase):
    def create(self, event: TaskEvent) -> TaskEvent:
        orm = TaskEventORM(
            user_id=event.user_id,
            task_id=event.task_id,
            event_type=event.event_type,
            before=event.before,
            after=event.after,
            reason=event.reason,
            created_at=event.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return TaskEvent.model_validate(orm)

    def list_by_task(self, task_id: int, *, limit: int = 200) -> list[TaskEvent]:
        stmt = (
            select(TaskEventORM)
            .where(TaskEventORM.task_id == task_id)
            .order_by(TaskEventORM.created_at.desc(), TaskEventORM.id.desc())
            .limit(limit)
        )
        return [TaskEvent.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_user(self, user_id: int, *, limit: int = 500) -> list[TaskEvent]:
        stmt = (
            select(TaskEventORM)
            .where(TaskEventORM.user_id == user_id)
            .order_by(TaskEventORM.created_at.desc(), TaskEventORM.id.desc())
            .limit(limit)
        )
        return [TaskEvent.model_validate(orm) for orm in self._session.scalars(stmt).all()]


__all__ = ["TaskEventRepository"]
