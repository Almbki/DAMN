"""ORM model for the daily_plans table (phase 4 daily schedule snapshot)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class DailyPlan(Base):
    __tablename__ = "daily_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    capacity_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: Task ids placed on the day (name matches DailyPlanRecord.tasks).
    tasks: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    def __repr__(self) -> str:
        return f"<DailyPlan plan={self.plan_id} date={self.date}>"


__all__ = ["DailyPlan"]
