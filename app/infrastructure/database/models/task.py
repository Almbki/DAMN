"""ORM model for the ``tasks`` table."""

from __future__ import annotations

from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.enums import CognitiveLoad, Priority, TaskStatus
from app.infrastructure.database.base import Base, enum_values

if TYPE_CHECKING:
    from app.infrastructure.database.models.execution import TaskExecution
    from app.infrastructure.database.models.goal import Goal
    from app.infrastructure.database.models.plan import Plan
    from app.infrastructure.database.models.task_standard import TaskStandard


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_plan_id_scheduled_date", "plan_id", "scheduled_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False, index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), nullable=True, index=True)
    parent_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    estimated_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    predicted_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cognitive_load: Mapped[CognitiveLoad] = mapped_column(
        Enum(
            CognitiveLoad,
            values_callable=enum_values,
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=CognitiveLoad.MEDIUM,
    )
    priority: Mapped[Priority] = mapped_column(Integer, nullable=False, default=Priority.MEDIUM)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
        default=TaskStatus.PENDING,
    )
    completion_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_flexible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    plan: Mapped[Plan] = relationship("Plan", back_populates="tasks")
    goal: Mapped[Goal | None] = relationship("Goal", back_populates="tasks")
    # Self-referential subtask hierarchy.
    parent_task: Mapped[Task | None] = relationship(
        "Task",
        remote_side="Task.id",
        back_populates="subtasks",
        foreign_keys=[parent_task_id],
    )
    subtasks: Mapped[list[Task]] = relationship(
        "Task", back_populates="parent_task", foreign_keys=[parent_task_id]
    )
    standards: Mapped[list[TaskStandard]] = relationship("TaskStandard", back_populates="task")
    executions: Mapped[list[TaskExecution]] = relationship("TaskExecution", back_populates="task")

    def __repr__(self) -> str:
        return f"<Task id={self.id} plan_id={self.plan_id} title={self.title!r}>"