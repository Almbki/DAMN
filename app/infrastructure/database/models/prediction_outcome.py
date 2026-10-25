"""ORM model for prediction_outcomes: the observed result of one prediction."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("prediction_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    completion_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    #: execution / manual
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="execution", server_default="execution"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    def __repr__(self) -> str:
        return f"<PredictionOutcome snapshot={self.snapshot_id} task={self.task_id}>"


__all__ = ["PredictionOutcome"]
