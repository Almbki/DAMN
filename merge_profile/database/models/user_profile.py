"""ORM model for the ``user_profiles`` table.

One row per user (MBTI dimensions and identity text of the user profile).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    mbti_type: Mapped[str | None] = mapped_column(String(4), nullable=True)
    mbti_ie: Mapped[float | None] = mapped_column(Float, nullable=True)
    mbti_sn: Mapped[float | None] = mapped_column(Float, nullable=True)
    mbti_tf: Mapped[float | None] = mapped_column(Float, nullable=True)
    mbti_jp: Mapped[float | None] = mapped_column(Float, nullable=True)
    identity: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    def __repr__(self) -> str:
        return (
            f"<UserProfileModel id={self.id} user_id={self.user_id} "
            f"mbti_type={self.mbti_type!r}>"
        )