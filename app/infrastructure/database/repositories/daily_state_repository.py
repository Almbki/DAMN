"""DailyState persistence: one Level-2 snapshot per user per day."""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select

from app.domain.models import DailyState
from app.infrastructure.database.models.daily_state import DailyState as DailyStateORM
from app.infrastructure.database.repositories.base import RepositoryBase

_FIELDS: tuple[str, ...] = (
    "fatigue",
    "stress",
    "self_efficacy",
    "fatigue_uncertainty",
    "stress_uncertainty",
    "self_efficacy_uncertainty",
    "evidence_availability",
    "evidence_count",
    "conflict",
    "next_day_prior",
    "next_day_uncertainty",
    "cold_start",
    "gap_days",
    "profile_json",
    "model_version",
    "config_version",
    "artifact_hash",
    "data_origin",
)


class DailyStateRepository(RepositoryBase):
    def upsert(self, state: DailyState) -> DailyState:
        """Create or replace the row for (user_id, date); keeps history per day."""
        orm = self._session.scalars(
            select(DailyStateORM)
            .where(DailyStateORM.user_id == state.user_id, DailyStateORM.date == state.date)
            .limit(1)
        ).first()
        if orm is None:
            orm = DailyStateORM(
                user_id=state.user_id,
                date=state.date,
                **{field: getattr(state, field) for field in _FIELDS},
            )
            self._session.add(orm)
        else:
            for field in _FIELDS:
                setattr(orm, field, getattr(state, field))
        self._session.flush()
        self._session.refresh(orm)
        return DailyState.model_validate(orm)

    def get_by_user_and_date(self, user_id: int, day: date) -> DailyState | None:
        orm = self._session.scalars(
            select(DailyStateORM)
            .where(DailyStateORM.user_id == user_id, DailyStateORM.date == day)
            .limit(1)
        ).first()
        return DailyState.model_validate(orm) if orm is not None else None

    def list_by_user(self, user_id: int, *, limit: int = 730) -> list[DailyState]:
        stmt = (
            select(DailyStateORM)
            .where(DailyStateORM.user_id == user_id)
            .order_by(DailyStateORM.date.desc())
            .limit(limit)
        )
        return [DailyState.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def prune_before(self, user_id: int, cutoff: date) -> int:
        """Delete this user's daily states strictly before the cutoff date."""
        result = self._session.execute(
            delete(DailyStateORM).where(
                DailyStateORM.user_id == user_id, DailyStateORM.date < cutoff
            )
        )
        return result.rowcount or 0

    def delete_by_user(self, user_id: int) -> int:
        result = self._session.execute(
            delete(DailyStateORM).where(DailyStateORM.user_id == user_id)
        )
        return result.rowcount or 0


__all__ = ["DailyStateRepository"]
