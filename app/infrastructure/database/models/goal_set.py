"""ORM model for the ``goal_sets`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import utcnow
from app.domain.models.enums import GoalSetStatus
from app.infrastructure.database.base import Base, enum_values

if TYPE_CHECKING:
    from app.infrastructure.database.models.goal import Goal


class GoalSet(Base):
    __tablename__ = "goal_sets"
    __table_args__ = (
        Index("ix_goal_sets_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[GoalSetStatus] = mapped_column(
        Enum(GoalSetStatus, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
        default=GoalSetStatus.ACTIVE,
        server_default=GoalSetStatus.ACTIVE.value,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    goals: Mapped[list[Goal]] = relationship("Goal", back_populates="goal_set")

    def __repr__(self) -> str:
        return f"<GoalSet id={self.id} name={self.name!r}>"
