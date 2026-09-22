"""ReplanEvent persistence (audit trail for plan adaptations)."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import ReplanEvent
from app.infrastructure.database.models.plan import Plan as PlanORM
from app.infrastructure.database.models.replan_event import ReplanEvent as ReplanEventORM
from app.infrastructure.database.repositories.base import RepositoryBase


class ReplanEventRepository(RepositoryBase):
    def create(self, event: ReplanEvent) -> ReplanEvent:
        orm = ReplanEventORM(
            plan_id=event.plan_id,
            trigger_type=event.trigger_type,
            reason=event.reason,
            old_version=event.old_version,
            new_version=event.new_version,
            changed_tasks=event.changed_tasks,
            created_at=event.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return ReplanEvent.model_validate(orm)

    def list_by_plan(self, plan_id: int) -> list[ReplanEvent]:
        stmt = (
            select(ReplanEventORM)
            .where(ReplanEventORM.plan_id == plan_id)
            .order_by(ReplanEventORM.id)
        )
        return [ReplanEvent.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def get_latest_for_plan(self, plan_id: int) -> ReplanEvent | None:
        stmt = (
            select(ReplanEventORM)
            .where(ReplanEventORM.plan_id == plan_id)
            .order_by(ReplanEventORM.id.desc())
            .limit(1)
        )
        orm = self._session.scalars(stmt).first()
        return ReplanEvent.model_validate(orm) if orm is not None else None

    def get_latest_for_user(self, user_id: int) -> ReplanEvent | None:
        """Latest replan across every plan owned by the user.

        Used for the user-level replan cooldown (rate limit), independent of
        which plan version the client is asking about.
        """
        stmt = (
            select(ReplanEventORM)
            .join(PlanORM, ReplanEventORM.plan_id == PlanORM.id)
            .where(PlanORM.user_id == user_id)
            .order_by(ReplanEventORM.id.desc())
            .limit(1)
        )
        orm = self._session.scalars(stmt).first()
        return ReplanEvent.model_validate(orm) if orm is not None else None