"""ORM model for ``shadow_predictions`` (Level 3 audit trail)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class ShadowPrediction(Base):
    __tablename__ = "shadow_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plans.id"), nullable=True, index=True
    )
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True, index=True
    )
    inference_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
    model_level: Mapped[str] = mapped_column(String(16), nullable=False, default="level3")
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    artifact_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    feature_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    production_decision: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    shadow_prediction: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    uncertainty: Mapped[float | None] = mapped_column(Float, nullable=True)
    disagreement: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="shadow")
    data_origin: Mapped[str] = mapped_column(
        String(16), nullable=False, default="real", server_default="real"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<ShadowPrediction user={self.user_id} task={self.task_id} "
            f"success={self.success} mode={self.mode}>"
        )