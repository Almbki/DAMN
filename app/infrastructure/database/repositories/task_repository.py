"""Task persistence."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import delete, select, update

from app.domain.models import Task
from app.infrastructure.database.models.plan import Plan as PlanORM
from app.infrastructure.database.models.task import Task as TaskORM
from app.infrastructure.database.repositories.base import RepositoryBase


class TaskRepository(RepositoryBase):
    def create_many(self, tasks: list[Task]) -> list[Task]:
        # `goal_id=0` is never a legal FK value. Catch it before SQLAlchemy
        # turns it into an opaque ForeignKeyViolation at flush time.
        invalid = [task.title for task in tasks if task.goal_id is not None and task.goal_id <= 0]
        if invalid:
            raise ValueError(
                f"tasks have invalid goal_id <= 0: {invalid[:5]}"
            )
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
                prediction_source=t.prediction_source,
                prediction_mode=t.prediction_mode,
                data_origin=t.data_origin,
                is_flexible=t.is_flexible,
                task_kind=t.task_kind,
                series_id=t.series_id,
                series_index=t.series_index,
                occurrence_date=t.occurrence_date,
                target_amount=t.target_amount,
                target_unit=t.target_unit,
                order_index=t.order_index,
                deleted_at=t.deleted_at,
                deleted_reason=t.deleted_reason,
            )
            for t in tasks
        ]
        self._session.add_all(orms)
        self._session.flush()
        for orm in orms:
            self._session.refresh(orm)
        return [self._to_domain(orm) for orm in orms]

    @staticmethod
    def _to_domain(orm: TaskORM) -> Task:
        return Task.model_validate(orm)

    def get_by_id(self, task_id: int, *, include_deleted: bool = False) -> Task | None:
        stmt = select(TaskORM).where(TaskORM.id == task_id)
        if not include_deleted:
            stmt = stmt.where(TaskORM.deleted_at.is_(None))
        orm = self._session.scalars(stmt).first()
        return self._to_domain(orm) if orm is not None else None

    def list_by_user(self, user_id: int, *, limit: int = 2000) -> list[Task]:
        """Every active task belonging to a user (across plan versions)."""
        stmt = (
            select(TaskORM)
            .join(PlanORM, TaskORM.plan_id == PlanORM.id)
            .where(PlanORM.user_id == user_id, TaskORM.deleted_at.is_(None))
            .order_by(TaskORM.scheduled_date, TaskORM.order_index, TaskORM.id)
            .limit(limit)
        )
        return [self._to_domain(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_plan(self, plan_id: int) -> list[Task]:
        stmt = (
            select(TaskORM)
            .where(TaskORM.plan_id == plan_id, TaskORM.deleted_at.is_(None))
            .order_by(TaskORM.order_index, TaskORM.scheduled_date, TaskORM.id)
        )
        return [self._to_domain(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_plan_and_date(self, plan_id: int, day: date) -> list[Task]:
        stmt = (
            select(TaskORM)
            .where(
                TaskORM.plan_id == plan_id,
                TaskORM.scheduled_date == day,
                TaskORM.deleted_at.is_(None),
            )
            .order_by(TaskORM.order_index, TaskORM.start_time, TaskORM.id)
        )
        return [self._to_domain(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_ids(self, task_ids: list[int]) -> list[Task]:
        if not task_ids:
            return []
        stmt = (
            select(TaskORM)
            .where(TaskORM.id.in_(task_ids), TaskORM.deleted_at.is_(None))
            .order_by(TaskORM.order_index, TaskORM.id)
        )
        return [self._to_domain(orm) for orm in self._session.scalars(stmt).all()]

    def update_fields(self, task_id: int, **fields: object) -> Task | None:
        orm = self._session.get(TaskORM, task_id)
        if orm is None or orm.deleted_at is not None:
            return None
        for field, value in fields.items():
            setattr(orm, field, value)
        self._session.flush()
        return self._to_domain(orm)

    def list_by_goal(self, goal_id: int) -> list[Task]:
        """Active (non-deleted) tasks referencing a goal (protects goal deletion)."""
        stmt = (
            select(TaskORM)
            .where(TaskORM.goal_id == goal_id, TaskORM.deleted_at.is_(None))
            .order_by(TaskORM.id)
        )
        return [self._to_domain(orm) for orm in self._session.scalars(stmt).all()]

    def soft_delete(self, task_id: int, reason: str | None = None) -> bool:
        """Mark a task deleted without removing its row.

        Idempotent: a second call keeps the original timestamp/reason and still
        returns ``True`` (the task exists). Returns ``False`` only when no such
        task exists. ``TaskExecution`` / ``TaskStandard`` rows are untouched.
        """
        orm = self._session.get(TaskORM, task_id)
        if orm is None:
            return False
        if orm.deleted_at is None:
            orm.deleted_at = datetime.now(UTC)
            orm.deleted_reason = reason
            self._session.flush()
        return True

    def detach_deleted_from_goal(self, goal_id: int) -> int:
        """Null the FK on soft-deleted tasks so the goal row can be removed."""
        self._session.flush()
        result = self._session.execute(
            update(TaskORM)
            .where(TaskORM.goal_id == goal_id, TaskORM.deleted_at.is_not(None))
            .values(goal_id=None)
        )
        return result.rowcount or 0

    def delete_by_plan(self, plan_id: int) -> int:
        """Delete every task of a plan; returns the number of deleted rows.

        Callers must remove dependent rows (task_standards, task_executions)
        first, or let the DB-side FK policy handle them.
        """
        self._session.flush()  # flush pending writes before the bulk delete
        result = self._session.execute(delete(TaskORM).where(TaskORM.plan_id == plan_id))
        return result.rowcount or 0