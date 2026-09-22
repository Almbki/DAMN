"""Goal persistence."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import Goal
from app.domain.models.enums import GoalStatus
from app.infrastructure.database.models.goal import Goal as GoalORM
from app.infrastructure.database.repositories.base import RepositoryBase


class GoalRepository(RepositoryBase):
    def create(self, goal: Goal) -> Goal:
        orm = GoalORM(
            user_id=goal.user_id,
            title=goal.title,
            description=goal.description,
            goal_type=goal.goal_type,
            deadline=goal.deadline,
            priority=goal.priority,
            status=goal.status,
            estimated_minutes=goal.estimated_minutes,
            options=goal.options,
            created_at=goal.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return Goal.model_validate(orm)

    def create_many(self, goals: list[Goal]) -> list[Goal]:
        orms = [
            GoalORM(
                user_id=g.user_id,
                title=g.title,
                description=g.description,
                goal_type=g.goal_type,
                deadline=g.deadline,
                priority=g.priority,
                status=g.status,
                estimated_minutes=g.estimated_minutes,
                options=g.options,
                created_at=g.created_at,
            )
            for g in goals
        ]
        self._session.add_all(orms)
        self._session.flush()
        for orm in orms:
            self._session.refresh(orm)
        return [Goal.model_validate(orm) for orm in orms]

    def get_by_id(self, goal_id: int) -> Goal | None:
        orm = self._session.get(GoalORM, goal_id)
        return Goal.model_validate(orm) if orm is not None else None

    def list_by_user(self, user_id: int) -> list[Goal]:
        stmt = (
            select(GoalORM)
            .where(GoalORM.user_id == user_id)
            .order_by(GoalORM.status, GoalORM.deadline.is_(None), GoalORM.id)
        )
        return [Goal.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_ids(self, goal_ids: list[int]) -> list[Goal]:
        if not goal_ids:
            return []
        stmt = select(GoalORM).where(GoalORM.id.in_(goal_ids)).order_by(GoalORM.id)
        return [Goal.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def update_status(self, goal_id: int, status: GoalStatus) -> Goal | None:
        orm = self._session.get(GoalORM, goal_id)
        if orm is None:
            return None
        orm.status = status
        self._session.flush()
        return Goal.model_validate(orm)

    def update_fields(self, goal_id: int, **fields: object) -> Goal | None:
        """Update arbitrary columns and return the refreshed domain model."""
        orm = self._session.get(GoalORM, goal_id)
        if orm is None:
            return None
        for key, value in fields.items():
            setattr(orm, key, value)
        self._session.flush()
        self._session.refresh(orm)
        return Goal.model_validate(orm)

    def delete(self, goal_id: int) -> bool:
        """Hard delete one goal; ``False`` when it does not exist."""
        orm = self._session.get(GoalORM, goal_id)
        if orm is None:
            return False
        self._session.delete(orm)
        self._session.flush()
        return True