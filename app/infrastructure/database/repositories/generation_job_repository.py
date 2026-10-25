"""GenerationJob persistence (durable async generation-job state)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.domain.models import GenerationJobRecord
from app.domain.models.base import utcnow
from app.infrastructure.database.models.generation_job import GenerationJobModel
from app.infrastructure.database.repositories.base import RepositoryBase

_ACTIVE_STATUSES = ("pending", "running")
#: Job kinds whose result may be a resumable preview (``thread_id`` + ``preview``).
_PREVIEW_KINDS = ("preview", "preview_adjust", "decompose")


class GenerationJobRepository(RepositoryBase):
    def create(self, record: GenerationJobRecord) -> GenerationJobRecord:
        orm = GenerationJobModel(
            job_id=record.job_id,
            user_id=record.user_id,
            kind=record.kind,
            status=record.status,
            plan_id=record.plan_id,
            result=record.result,
            error=record.error,
            events=list(record.events),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        self._session.add(orm)
        self._session.flush()
        self._session.refresh(orm)
        return GenerationJobRecord.model_validate(orm)

    def update_fields(self, job_id: str, **fields: Any) -> GenerationJobRecord | None:
        orm = self._session.get(GenerationJobModel, job_id)
        if orm is None:
            return None
        for key, value in fields.items():
            setattr(orm, key, value)
        self._session.flush()
        self._session.refresh(orm)
        return GenerationJobRecord.model_validate(orm)

    def upsert(self, record: GenerationJobRecord) -> GenerationJobRecord:
        """Insert the job or overwrite its mutable snapshot fields."""
        orm = self._session.get(GenerationJobModel, record.job_id)
        if orm is None:
            return self.create(record)
        orm.user_id = record.user_id
        orm.kind = record.kind
        orm.status = record.status
        orm.plan_id = record.plan_id
        orm.result = record.result
        orm.error = record.error
        orm.events = list(record.events)
        orm.created_at = record.created_at
        orm.updated_at = record.updated_at
        self._session.flush()
        self._session.refresh(orm)
        return GenerationJobRecord.model_validate(orm)

    def get_by_job_id(self, job_id: str) -> GenerationJobRecord | None:
        orm = self._session.get(GenerationJobModel, job_id)
        return GenerationJobRecord.model_validate(orm) if orm is not None else None

    def list_by_user(
        self,
        user_id: int,
        *,
        kinds: Sequence[str] | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[GenerationJobRecord]:
        stmt = select(GenerationJobModel).where(GenerationJobModel.user_id == user_id)
        if kinds is not None:
            stmt = stmt.where(GenerationJobModel.kind.in_(tuple(kinds)))
        if status is not None:
            stmt = stmt.where(GenerationJobModel.status == status)
        stmt = stmt.order_by(GenerationJobModel.created_at.desc()).limit(limit)
        return [
            GenerationJobRecord.model_validate(orm)
            for orm in self._session.scalars(stmt).all()
        ]

    def latest_actionable_preview(
        self, user_id: int, *, limit: int = 50
    ) -> GenerationJobRecord | None:
        """Newest completed preview-like job whose result can be resumed.

        A result is actionable when it still carries a ``thread_id`` and a
        ``preview`` payload. Whether the underlying LangGraph checkpoint has
        since expired is not knowable here; confirm will answer 404/return the
        existing plan in that case.
        """
        for record in self.list_by_user(
            user_id, kinds=_PREVIEW_KINDS, status="completed", limit=limit
        ):
            result = record.result
            if (
                isinstance(result, dict)
                and isinstance(result.get("thread_id"), str)
                and isinstance(result.get("preview"), dict)
            ):
                return record
        return None

    def fail_active_jobs(self, error: str, *, now: datetime | None = None) -> int:
        """Mark every pending/running job as failed (startup crash recovery)."""
        stamp = now or utcnow()
        rows = self._session.scalars(
            select(GenerationJobModel).where(
                GenerationJobModel.status.in_(_ACTIVE_STATUSES)
            )
        ).all()
        for orm in rows:
            orm.status = "failed"
            orm.error = error
            orm.updated_at = stamp
        self._session.flush()
        return len(rows)


__all__ = ["GenerationJobRepository"]
