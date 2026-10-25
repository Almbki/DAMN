"""ORM model for the ``users`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.execution import TaskExecution
    from app.infrastructure.database.models.feedback import Feedback
    from app.infrastructure.database.models.goal import Goal
    from app.infrastructure.database.models.plan import Plan


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    execution_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    #: Dedicated column for SchedulingPreferences so a wholesale `profile` update
    #: (PATCH /users/me) can never clobber the scheduling settings. Added in
    #: revision 8b1f... (see docs/database/数据库迁移.md). Nullable so the
    #: migration is safe for existing rows; readers normalise NULL to {}.
    scheduling_preferences: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    # --- user portrait (static part of the profile engine, P3) ------------
    #: MBTI is a SOFT self-report input, never a diagnosis.
    mbti_type: Mapped[str | None] = mapped_column(String(4), nullable=True)
    #: Per-dimension weights {"ie","sn","tf","jp"} -> [0, 1]; NULL = not answered.
    mbti_dims: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=None)
    identity: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # --- Level 1 real trait model (IPIP-NEO-120 CAT output) ---------------
    #: Validated TraitProfileV1 JSON. This is the authoritative stable-trait
    #: record; the legacy MBTI columns above remain only as a soft self-report.
    trait_profile: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    trait_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trait_artifact_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trait_feature_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    goals: Mapped[list[Goal]] = relationship("Goal", back_populates="user")
    plans: Mapped[list[Plan]] = relationship("Plan", back_populates="user")
    task_executions: Mapped[list[TaskExecution]] = relationship(
        "TaskExecution", back_populates="user"
    )
    feedbacks: Mapped[list[Feedback]] = relationship("Feedback", back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"