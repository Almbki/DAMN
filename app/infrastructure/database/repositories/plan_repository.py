"""Plan persistence.

Plans are immutable versions: replanning inserts a new row with version + 1.
"""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import Plan
from app.domain.models.enums import PlanStatus
from app.infrastructure.database.models.plan import Plan as PlanORM
from app.infrastructure.database.repositories.base import RepositoryBase


class PlanRepository(RepositoryBase):
    def create(self, plan: Plan) -> Plan:
        orm = PlanORM(
            user_id=plan.user_id,
            version=plan.version,
            status=plan.status,
            title=plan.title,
            start_date=plan.start_date,
            end_date=plan.end_date,
            parent_plan_id=plan.parent_plan_id,
            confidence=plan.confidence,
            created_at=plan.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return Plan.model_validate(orm)

    def get_by_id(self, plan_id: int) -> Plan | None:
        orm = self._session.get(PlanORM, plan_id)
        return Plan.model_validate(orm) if orm is not None else None

    def list_by_user(self, user_id: int) -> list[Plan]:
        stmt = (
            select(PlanORM)
            .where(PlanORM.user_id == user_id)
            .order_by(PlanORM.version.desc(), PlanORM.id.desc())
        )
        return [Plan.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def get_latest_by_user(self, user_id: int) -> Plan | None:
        stmt = (
            select(PlanORM)
            .where(PlanORM.user_id == user_id)
            .order_by(PlanORM.version.desc(), PlanORM.id.desc())
            .limit(1)
        )
        orm = self._session.scalars(stmt).first()
        return Plan.model_validate(orm) if orm is not None else None

    def next_version(self, user_id: int) -> int:
        latest = self.get_latest_by_user(user_id)
        return latest.version + 1 if latest is not None else 1

    def update_status(self, plan_id: int, status: PlanStatus) -> Plan | None:
        orm = self._session.get(PlanORM, plan_id)
        if orm is None:
            return None
        orm.status = status
        self._session.flush()
        return Plan.model_validate(orm)