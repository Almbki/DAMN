"""ScheduleEvent persistence.

Repositories never commit - the service layer owns the transaction.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import and_, or_, select

from app.domain.models import ScheduleEvent
from app.infrastructure.database.models.schedule_event import (
    ScheduleEvent as ScheduleEventORM,
)
from app.infrastructure.database.repositories.base import RepositoryBase

#: Columns an upsert is allowed to overwrite. ``id`` / ``created_at`` are stable.
_MUTABLE_FIELDS = (
    "title",
    "event_kind",
    "start_date",
    "end_date",
    "start_time",
    "end_time",
    "weekdays",
    "source",
    "location",
    "teacher",
    "notes",
)


class ScheduleEventRepository(RepositoryBase):
    # -- reads -------------------------------------------------------------
    def get_by_id(
        self, event_id: int, *, include_deleted: bool = False
    ) -> ScheduleEvent | None:
        stmt = select(ScheduleEventORM).where(ScheduleEventORM.id == event_id)
        if not include_deleted:
            stmt = stmt.where(ScheduleEventORM.deleted_at.is_(None))
        orm = self._session.scalars(stmt).first()
        return ScheduleEvent.model_validate(orm) if orm is not None else None

    def get_by_uid(self, user_id: int, external_uid: str) -> ScheduleEvent | None:
        stmt = select(ScheduleEventORM).where(
            ScheduleEventORM.user_id == user_id,
            ScheduleEventORM.external_uid == external_uid,
        )
        orm = self._session.scalars(stmt).first()
        return ScheduleEvent.model_validate(orm) if orm is not None else None

    def list_by_user(
        self, user_id: int, *, include_deleted: bool = False
    ) -> list[ScheduleEvent]:
        stmt = select(ScheduleEventORM).where(ScheduleEventORM.user_id == user_id)
        if not include_deleted:
            stmt = stmt.where(ScheduleEventORM.deleted_at.is_(None))
        stmt = stmt.order_by(
            ScheduleEventORM.start_date, ScheduleEventORM.start_time, ScheduleEventORM.id
        )
        return [ScheduleEvent.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    def list_range(
        self, user_id: int, start: date, end: date, *, include_deleted: bool = False
    ) -> list[ScheduleEvent]:
        """Events that can occur inside ``[start, end]``.

        The date query is an overlap test; open-ended weekly recurrences are
        included because their concrete dates are expanded by the caller.
        """
        event = ScheduleEventORM
        overlap = or_(
            # No bounds at all: a pure weekly recurrence.
            and_(event.start_date.is_(None), event.end_date.is_(None)),
            # Open-ended from ``start_date`` onwards.
            and_(
                event.start_date.is_not(None),
                event.end_date.is_(None),
                event.start_date <= end,
            ),
            # Bounded above only.
            and_(
                event.start_date.is_(None),
                event.end_date.is_not(None),
                event.end_date >= start,
            ),
            # Fully bounded.
            and_(event.start_date <= end, event.end_date >= start),
        )
        stmt = select(event).where(event.user_id == user_id, overlap)
        if not include_deleted:
            stmt = stmt.where(event.deleted_at.is_(None))
        stmt = stmt.order_by(event.start_date, event.start_time, event.id)
        return [ScheduleEvent.model_validate(orm) for orm in self._session.scalars(stmt).all()]

    # -- writes ------------------------------------------------------------
    def upsert_by_uid(self, event: ScheduleEvent) -> tuple[ScheduleEvent, bool]:
        """Insert or update keyed by ``(user_id, external_uid)``.

        Returns ``(event, created)``. A soft-deleted match is revived.
        """
        if not event.external_uid:
            raise ValueError("external_uid is required for an upsert")

        orm = self._session.scalars(
            select(ScheduleEventORM).where(
                ScheduleEventORM.user_id == event.user_id,
                ScheduleEventORM.external_uid == event.external_uid,
            )
        ).first()

        if orm is None:
            orm = ScheduleEventORM(
                user_id=event.user_id,
                external_uid=event.external_uid,
                title=event.title,
                event_kind=event.event_kind,
                start_date=event.start_date,
                end_date=event.end_date,
                start_time=event.start_time,
                end_time=event.end_time,
                weekdays=event.weekdays,
                source=event.source,
                location=event.location,
                teacher=event.teacher,
                notes=event.notes,
                created_at=event.created_at,
                updated_at=event.updated_at,
            )
            self._session.add(orm)
            self._session.flush()
            self._session.refresh(orm)
            return ScheduleEvent.model_validate(orm), True

        for field in _MUTABLE_FIELDS:
            setattr(orm, field, getattr(event, field))
        orm.external_uid = event.external_uid
        orm.deleted_at = None
        orm.updated_at = datetime.now(UTC)
        self._session.flush()
        self._session.refresh(orm)
        return ScheduleEvent.model_validate(orm), False

    def soft_delete(self, event_id: int, *, user_id: int | None = None) -> bool:
        """Mark an event deleted; ``False`` when missing or already deleted."""
        orm = self._session.get(ScheduleEventORM, event_id)
        if orm is None or orm.deleted_at is not None:
            return False
        if user_id is not None and orm.user_id != user_id:
            return False
        orm.deleted_at = datetime.now(UTC)
        self._session.flush()
        return True


__all__ = ["ScheduleEventRepository"]
