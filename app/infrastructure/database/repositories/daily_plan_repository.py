"""DailyPlan persistence (phase 4 per-day schedule snapshots)."""

from __future__ import annotations

from sqlalchemy import delete, select

from app.domain.models.daily_plan import DailyPlanRecord
from app.infrastructure.database.models.daily_plan import DailyPlan as DailyPlanORM
from app.infrastructure.database.repositories.base import RepositoryBase


class DailyPlanRepository(RepositoryBase):
    """Session-bound daily-plan writes/reads. Never commits - flush only."""

    @staticmethod
    def _to_orm(record: DailyPlanRecord) -> DailyPlanORM:
        return DailyPlanORM(
            plan_id=record.plan_id,
            date=record.date,
            capacity_minutes=record.capacity_minutes,
            used_minutes=record.used_minutes,
            tasks=list(record.tasks),
            reasons=list(record.reasons),
            created_at=record.created_at,
        )

    def create_many(self, plans: list[DailyPlanRecord]) -> list[DailyPlanRecord]:
        orms = [self._to_orm(record) for record in plans]
        self._session.add_all(orms)
        self._session.flush()
        for orm in orms:
            self._session.refresh(orm)
        return [DailyPlanRecord.model_validate(orm) for orm in orms]

    def list_by_plan(self, plan_id: int) -> list[DailyPlanRecord]:
        stmt = (
            select(DailyPlanORM)
            .where(DailyPlanORM.plan_id == plan_id)
            .order_by(DailyPlanORM.date, DailyPlanORM.id)
        )
        return [
            DailyPlanRecord.model_validate(orm)
            for orm in self._session.scalars(stmt).all()
        ]

    def delete_by_plan(self, plan_id: int) -> int:
        result = self._session.execute(
            delete(DailyPlanORM).where(DailyPlanORM.plan_id == plan_id)
        )
        return result.rowcount or 0


__all__ = ["DailyPlanRepository"]
