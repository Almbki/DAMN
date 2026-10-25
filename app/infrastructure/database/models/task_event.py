"""ORM model for the append-only task_events table."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class TaskEvent(Base):
    """One recorded task change. Rows are only ever appended."""

    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # created / status_changed / edited / rescheduled / corrected / deleted
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    def __repr__(self) -> str:
        return f"<TaskEvent task={self.task_id} type={self.event_type}>"


__all__ = ["TaskEvent"]
