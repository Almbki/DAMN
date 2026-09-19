"""ORM model for the ``feedbacks`` table."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import utcnow
from app.domain.models.enums import TimeOfDay
from app.infrastructure.database.base import Base, enum_values

if TYPE_CHECKING:
    from app.infrastructure.database.models.plan import Plan
    from app.infrastructure.database.models.user import User


class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = (
        Index("ix_feedbacks_user_id_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stress_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delay_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    free_text: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    dominant_time_of_day: Mapped[TimeOfDay | None] = mapped_column(
        Enum(TimeOfDay, values_callable=enum_values, native_enum=False, length=32),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    user: Mapped[User] = relationship("User", back_populates="feedbacks")
    plan: Mapped[Plan] = relationship("Plan", back_populates="feedbacks")

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} plan_id={self.plan_id} date={self.date}>"