"""Goal-set persistence."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import GoalSet
from app.domain.models.enums import GoalSetStatus
from app.infrastructure.database.models.goal_set import GoalSet as GoalSetORM
from app.infrastructure.database.repositories.base import RepositoryBase


class GoalSetRepository(RepositoryBase):
    def create(self, goal_set: GoalSet) -> GoalSet:
        orm = GoalSetORM(
            user_id=goal_set.user_id,
            name=goal_set.name,
            description=goal_set.description,
            status=goal_set.status,
            archived_at=goal_set.archived_at,
            created_at=goal_set.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return GoalSet.model_validate(orm)

    def get_by_id(self, goal_set_id: int) -> GoalSet | None:
        orm = self._session.get(GoalSetORM, goal_set_id)
        return GoalSet.model_validate(orm) if orm is not None else None

    def list_by_user(
        self, user_id: int, *, include_archived: bool = True
    ) -> list[GoalSet]:
        stmt = (
            select(GoalSetORM)
            .where(GoalSetORM.user_id == user_id)
            .order_by(GoalSetORM.created_at.desc(), GoalSetORM.id.desc())
        )
        if not include_archived:
            stmt = stmt.where(GoalSetORM.status == GoalSetStatus.ACTIVE)
        return [GoalSet.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_active(self, user_id: int) -> list[GoalSet]:
        return self.list_by_user(user_id, include_archived=False)

    def update_fields(self, goal_set_id: int, **fields: object) -> GoalSet | None:
        orm = self._session.get(GoalSetORM, goal_set_id)
        if orm is None:
            return None
        for key, value in fields.items():
            setattr(orm, key, value)
        self._session.flush()
        self._session.refresh(orm)
        return GoalSet.model_validate(orm)


__all__ = ["GoalSetRepository"]
