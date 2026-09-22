"""ORM model for the ``task_standards`` table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.task import Task


class TaskStandard(Base):
    __tablename__ = "task_standards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    estimated_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    task: Mapped[Task] = relationship("Task", back_populates="standards")

    def __repr__(self) -> str:
        return f"<TaskStandard id={self.id} task_id={self.task_id}>"