"""Feedback persistence (daily check-ins)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.domain.models import Feedback
from app.infrastructure.database.models.feedback import Feedback as FeedbackORM
from app.infrastructure.database.repositories.base import RepositoryBase


class FeedbackRepository(RepositoryBase):
    def create(self, feedback: Feedback) -> Feedback:
        orm = FeedbackORM(
            user_id=feedback.user_id,
            plan_id=feedback.plan_id,
            date=feedback.date,
            completion_rate=feedback.completion_rate,
            stress_level=feedback.stress_level,
            energy_level=feedback.energy_level,
            delay_reason=feedback.delay_reason,
            free_text=feedback.free_text,
            sleep_hours=feedback.sleep_hours,
            dominant_time_of_day=feedback.dominant_time_of_day,
            created_at=feedback.created_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return Feedback.model_validate(orm)

    def list_by_plan(self, plan_id: int) -> list[Feedback]:
        stmt = (
            select(FeedbackORM)
            .where(FeedbackORM.plan_id == plan_id)
            .order_by(FeedbackORM.date, FeedbackORM.id)
        )
        return [Feedback.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_by_user(self, user_id: int, limit: int = 200) -> list[Feedback]:
        stmt = (
            select(FeedbackORM)
            .where(FeedbackORM.user_id == user_id)
            .order_by(FeedbackORM.date.desc(), FeedbackORM.id.desc())
            .limit(limit)
        )
        return [Feedback.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def get_by_plan_and_date(self, plan_id: int, day: date) -> Feedback | None:
        stmt = select(FeedbackORM).where(
            FeedbackORM.plan_id == plan_id, FeedbackORM.date == day
        )
        orm = self._session.scalars(stmt).first()
        return Feedback.model_validate(orm) if orm is not None else None