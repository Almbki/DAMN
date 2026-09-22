"""ORM model for the ``plans`` table."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import utcnow
from app.domain.models.enums import PlanStatus
from app.infrastructure.database.base import Base, enum_values

if TYPE_CHECKING:
    from app.infrastructure.database.models.feedback import Feedback
    from app.infrastructure.database.models.replan_event import ReplanEvent
    from app.infrastructure.database.models.task import Task
    from app.infrastructure.database.models.user import User


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        UniqueConstraint("user_id", "version", name="uq_plans_user_id_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[PlanStatus] = mapped_column(
        Enum(PlanStatus, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
        default=PlanStatus.DRAFT,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    parent_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plans.id"), nullable=True, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    user: Mapped[User] = relationship("User", back_populates="plans")
    # Self-referential chain of plan versions.
    parent_plan: Mapped[Plan | None] = relationship(
        "Plan",
        remote_side="Plan.id",
        back_populates="child_plans",
        foreign_keys=[parent_plan_id],
    )
    child_plans: Mapped[list[Plan]] = relationship(
        "Plan", back_populates="parent_plan", foreign_keys=[parent_plan_id]
    )
    tasks: Mapped[list[Task]] = relationship("Task", back_populates="plan")
    feedbacks: Mapped[list[Feedback]] = relationship("Feedback", back_populates="plan")
    replan_events: Mapped[list[ReplanEvent]] = relationship("ReplanEvent", back_populates="plan")

    def __repr__(self) -> str:
        return f"<Plan id={self.id} user_id={self.user_id} version={self.version}>"