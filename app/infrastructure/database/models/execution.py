"""ORM model for the ``task_executions`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import utcnow
from app.domain.models.enums import TimeOfDay
from app.infrastructure.database.base import Base, enum_values

if TYPE_CHECKING:
    from app.infrastructure.database.models.task import Task
    from app.infrastructure.database.models.user import User


class TaskExecution(Base):
    __tablename__ = "task_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    planned_duration: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    difficulty_feedback: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    time_of_day: Mapped[TimeOfDay | None] = mapped_column(
        Enum(TimeOfDay, values_callable=enum_values, native_enum=False, length=32),
        nullable=True,
    )
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    task: Mapped[Task] = relationship("Task", back_populates="executions")
    user: Mapped[User] = relationship("User", back_populates="task_executions")

    def __repr__(self) -> str:
        return f"<TaskExecution id={self.id} task_id={self.task_id}>"