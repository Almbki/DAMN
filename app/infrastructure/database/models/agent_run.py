"""ORM model for the ``agent_runs`` table (audit trail for agent executions)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import utcnow
from app.infrastructure.database.base import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: Correlates with the LangGraph thread_id used for preview state.
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plans.id"), nullable=True, index=True
    )
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False, default="initial_plan")
    graph_version: Mapped[str] = mapped_column(String(32), nullable=False, default="planner-v1")
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nodes_executed: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    tool_calls: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    llm_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ml_prediction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    def __repr__(self) -> str:
        return f"<AgentRun run_id={self.run_id} status={self.status}>"
