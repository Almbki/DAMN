"""ORM model for the ``user_states`` table.

One row per user (adaptive planner runtime state driven by feedback).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class UserStateModel(Base):
    __tablename__ = "user_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    duration_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.3)
    completion_prob: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    stress_baseline: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    energy_drain_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    proactive_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    procrastination_tendency: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5
    )
    preferred_time_slots: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    stress_response: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    state_energy: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    state_fatigue: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    self_efficacy: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    update_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    def __repr__(self) -> str:
        return f"<UserStateModel id={self.id} user_id={self.user_id}>"