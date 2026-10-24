"""ORM model for the ``user_states`` table.

One row per user (adaptive planner runtime state driven by feedback).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String
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
    # --- Level 2 real dynamic state (DDSR-V1) ----------------------------
    #: Flattened projections of the last validated Level 2 profile. The JSON
    #: column below is the audit source of truth; the floats are query-friendly
    #: projections and are never independently estimated.
    state_stress: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    state_fatigue_uncertainty: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.25
    )
    state_stress_uncertainty: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.25
    )
    self_efficacy_uncertainty: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.25
    )
    level2_profile: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    level2_profile_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    level2_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level2_config_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level2_artifact_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level2_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    def __repr__(self) -> str:
        return f"<UserStateModel id={self.id} user_id={self.user_id}>"