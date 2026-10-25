"""ORM model for daily_states: one Level-2 state snapshot per user per day."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class DailyState(Base):
    __tablename__ = "daily_states"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_states_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fatigue: Mapped[float] = mapped_column(Float, nullable=False)
    stress: Mapped[float] = mapped_column(Float, nullable=False)
    self_efficacy: Mapped[float] = mapped_column(Float, nullable=False)
    fatigue_uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    stress_uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    self_efficacy_uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_availability: Mapped[str] = mapped_column(
        String(32), nullable=False, default="none", server_default="none"
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    conflict: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    next_day_prior: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    next_day_uncertainty: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    cold_start: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    gap_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    #: Full auditable DynamicStateProfile JSON.
    profile_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    config_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    data_origin: Mapped[str] = mapped_column(
        String(16), nullable=False, default="real", server_default="real"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    def __repr__(self) -> str:
        return f"<DailyState user={self.user_id} date={self.date}>"


__all__ = ["DailyState"]
