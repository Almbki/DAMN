"""ORM model for resumable Level 1 CAT assessments."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class TraitAssessmentModel(Base):
    __tablename__ = "trait_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="in_progress", index=True
    )
    #: Ordered [{"item_id": ..., "response": 1..5}, ...] - no model arrays.
    responses: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    rr_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unavailable: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    current_item_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    calibration_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    feature_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    trait_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    data_origin: Mapped[str] = mapped_column(
        String(16), nullable=False, default="real", server_default="real"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<TraitAssessment {self.id} user={self.user_id} status={self.status}>"