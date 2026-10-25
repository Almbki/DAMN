"""ORM model for evidence_items (reflection evidence extracted in Level 2)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feedback_id: Mapped[int | None] = mapped_column(
        ForeignKey("feedbacks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # day_review / stuck_points / state_review / tomorrow_outlook
    reflection_field: Mapped[str] = mapped_column(String(32), nullable=False)
    # fatigue / stress / self_efficacy / procrastination / interruption
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    strength: Mapped[str] = mapped_column(String(16), nullable=False)
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    cause_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    voluntary: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    #: Must be a verbatim substring of the reflection text.
    evidence_text: Mapped[str] = mapped_column(String(500), nullable=False)
    extractor: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(32), nullable=False)
    # accepted / rejected
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    def __repr__(self) -> str:
        return f"<EvidenceItem id={self.id} type={self.evidence_type}>"


__all__ = ["EvidenceItem"]
