"""ORM model for the ``replan_events`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import utcnow
from app.domain.models.enums import ReplanTriggerType
from app.infrastructure.database.base import Base, enum_values

if TYPE_CHECKING:
    from app.infrastructure.database.models.plan import Plan


class ReplanEvent(Base):
    __tablename__ = "replan_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False, index=True)
    trigger_type: Mapped[ReplanTriggerType] = mapped_column(
        Enum(
            ReplanTriggerType,
            values_callable=enum_values,
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=ReplanTriggerType.MANUAL,
    )
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    old_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    new_version: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    changed_tasks: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    plan: Mapped[Plan] = relationship("Plan", back_populates="replan_events")

    def __repr__(self) -> str:
        return f"<ReplanEvent id={self.id} plan_id={self.plan_id}>"