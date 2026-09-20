"""ORM model for the ``user_models`` table.

One row per user (statistical factors derived from execution history).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.user import User


class UserModel(Base):
    __tablename__ = "user_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="statistical-v0")
    duration_factors: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    completion_probability: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    stress_response: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    preferred_time_slots: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    user: Mapped[User] = relationship("User", back_populates="user_models")

    def __repr__(self) -> str:
        return f"<UserModel id={self.id} user_id={self.user_id}>"