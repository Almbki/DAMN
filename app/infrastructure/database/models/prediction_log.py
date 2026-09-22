"""ORM model for the ``prediction_logs`` table.

Every prediction is recorded with its model version, a feature fingerprint and
the truthful ``source``, so it can later be joined with ``task_executions`` to
score the predictor (MAE / Brier / calibration).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plans.id"), nullable=True, index=True
    )
    #: Null for plan-level predictions (e.g. the adjustment route).
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True, index=True
    )
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    #: duration | completion | stress | time_slot | adjustment
    prediction_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    feature_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    predicted: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    #: mock:statistical | fallback:rule | llm | <real model name>
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    def __repr__(self) -> str:
        return f"<PredictionLog {self.prediction_type} source={self.source}>"
