"""ORM model for prediction_snapshots: frozen Level-3 inputs at prediction time."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class PredictionSnapshot(Base):
    """Predict-time input freeze. Never back-filled with post-task information."""

    __tablename__ = "prediction_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    prediction_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    trait: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    task: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    history: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    feature_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    config_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    #: shadow (this version only ever runs shadow)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="shadow")
    data_origin: Mapped[str] = mapped_column(
        String(16), nullable=False, default="real", server_default="real"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    def __repr__(self) -> str:
        return f"<PredictionSnapshot task={self.task_id} at={self.prediction_timestamp}>"


__all__ = ["PredictionSnapshot"]
