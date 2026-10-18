"""ORM model for the ``goals`` table."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import utcnow
from app.domain.models.enums import GoalStatus, GoalType, Priority, TaskKind
from app.infrastructure.database.base import Base, enum_values

if TYPE_CHECKING:
    from app.infrastructure.database.models.task import Task
    from app.infrastructure.database.models.user import User


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    goal_type: Mapped[GoalType] = mapped_column(
        Enum(GoalType, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
        default=GoalType.SHORT_TERM,
    )
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[Priority] = mapped_column(Integer, nullable=False, default=Priority.MEDIUM)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
        default=GoalStatus.ACTIVE,
    )
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    task_kind: Mapped[TaskKind | None] = mapped_column(
        Enum(TaskKind, values_callable=enum_values, native_enum=False, length=32),
        nullable=True,
    )
    daily_target_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recurrence_weekdays: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    target_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    options: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    user: Mapped[User] = relationship("User", back_populates="goals")
    tasks: Mapped[list[Task]] = relationship("Task", back_populates="goal")

    def __repr__(self) -> str:
        return f"<Goal id={self.id} title={self.title!r}>"