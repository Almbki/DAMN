"""AgentRun persistence (audit trail for agent executions)."""

from __future__ import annotations

from sqlalchemy import select

from app.domain.models import AgentRun
from app.infrastructure.database.models.agent_run import AgentRun as AgentRunORM
from app.infrastructure.database.repositories.base import RepositoryBase


class AgentRunRepository(RepositoryBase):
    def create(self, run: AgentRun) -> AgentRun:
        orm = AgentRunORM(
            run_id=run.run_id,
            user_id=run.user_id,
            plan_id=run.plan_id,
            trigger_type=run.trigger_type,
            graph_version=run.graph_version,
            prompt_version=run.prompt_version,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            nodes_executed=run.nodes_executed,
            tool_calls=run.tool_calls,
            llm_calls=run.llm_calls,
            ml_prediction_id=run.ml_prediction_id,
            result_summary=run.result_summary,
            error=run.error,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return AgentRun.model_validate(orm)

    def update_fields(self, run_id: str, **fields: object) -> AgentRun | None:
        orm = self._session.scalars(
            select(AgentRunORM).where(AgentRunORM.run_id == run_id)
        ).first()
        if orm is None:
            return None
        for key, value in fields.items():
            setattr(orm, key, value)
        self._session.flush()
        self._session.refresh(orm)
        return AgentRun.model_validate(orm)

    def get_by_run_id(self, run_id: str) -> AgentRun | None:
        orm = self._session.scalars(
            select(AgentRunORM).where(AgentRunORM.run_id == run_id)
        ).first()
        return AgentRun.model_validate(orm) if orm is not None else None

    def list_by_user(self, user_id: int, limit: int = 50) -> list[AgentRun]:
        stmt = (
            select(AgentRunORM)
            .where(AgentRunORM.user_id == user_id)
            .order_by(AgentRunORM.id.desc())
            .limit(limit)
        )
        return [AgentRun.model_validate(orm) for orm in self._session.scalars(stmt).all()]


__all__ = ["AgentRunRepository"]
