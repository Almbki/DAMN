"""UnscheduledTask persistence (phase 4 scheduling reasons)."""

from __future__ import annotations

from sqlalchemy import delete, select

from app.domain.models.unscheduled_task import UnscheduledTaskRecord
from app.infrastructure.database.models.unscheduled_task import (
    UnscheduledTask as UnscheduledTaskORM,
)
from app.infrastructure.database.repositories.base import RepositoryBase


class UnscheduledTaskRepository(RepositoryBase):
    """Session-bound unscheduled-task writes/reads. Never commits - flush only."""

    @staticmethod
    def _to_orm(record: UnscheduledTaskRecord) -> UnscheduledTaskORM:
        return UnscheduledTaskORM(
            plan_id=record.plan_id,
            task_id=record.task_id,
            date=record.date,
            reason=record.reason,
            created_at=record.created_at,
        )

    def create_many(
        self, tasks: list[UnscheduledTaskRecord]
    ) -> list[UnscheduledTaskRecord]:
        orms = [self._to_orm(record) for record in tasks]
        self._session.add_all(orms)
        self._session.flush()
        for orm in orms:
            self._session.refresh(orm)
        return [UnscheduledTaskRecord.model_validate(orm) for orm in orms]

    def list_by_plan(self, plan_id: int) -> list[UnscheduledTaskRecord]:
        stmt = (
            select(UnscheduledTaskORM)
            .where(UnscheduledTaskORM.plan_id == plan_id)
            .order_by(UnscheduledTaskORM.date, UnscheduledTaskORM.id)
        )
        return [
            UnscheduledTaskRecord.model_validate(orm)
            for orm in self._session.scalars(stmt).all()
        ]

    def delete_by_plan(self, plan_id: int) -> int:
        result = self._session.execute(
            delete(UnscheduledTaskORM).where(UnscheduledTaskORM.plan_id == plan_id)
        )
        return result.rowcount or 0


__all__ = ["UnscheduledTaskRepository"]
