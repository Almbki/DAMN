"""Course / timetable import and listing.

The service owns the transaction: the repository only flushes. Imports are
tolerant (invalid rows become warnings) and idempotent (``(user_id,
external_uid)`` upsert, with a stable hash for rows without a uid).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.application.dto.schedule_import import ScheduleImportData
from app.application.exceptions import DomainValidationError, NotFoundError
from app.application.schedule_import import (
    MAX_FILE_BYTES,
    ParsedRow,
    parse_schedule_file,
)
from app.domain.models import ScheduleEvent, Task
from app.domain.models.enums import TaskStatus
from app.domain.scheduling.fixed_events import (
    event_occurs_on,
    events_overlap,
    time_overlap,
)
from app.infrastructure.database.repositories import (
    PlanRepository,
    ScheduleEventRepository,
    TaskRepository,
)

#: Cap the conflict list so a pathological file cannot produce a huge response.
MAX_CONFLICTS = 100


class ScheduleEventService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._events = ScheduleEventRepository(session)
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)

    # -- import ------------------------------------------------------------
    def import_file(
        self,
        user_id: int,
        *,
        filename: str,
        content: bytes,
        dry_run: bool = False,
        term_start: date | None = None,
    ) -> ScheduleImportData:
        if len(content) > MAX_FILE_BYTES:
            raise DomainValidationError(
                "file is too large: the limit is 2 MB"
            )

        outcome = parse_schedule_file(
            content,
            filename=filename,
            user_id=user_id,
            term_start=term_start,
        )
        imported = 0
        updated = 0

        for parsed in outcome.rows:
            existing = self._events.get_by_uid(user_id, parsed.event.external_uid or "")
            if existing is not None:
                updated += 1
            else:
                imported += 1

            if dry_run:
                continue
            self._events.upsert_by_uid(parsed.event)

        if not dry_run:
            self._session.commit()

        conflicts = self._conflicts(user_id, outcome.rows)
        return ScheduleImportData(
            imported=imported,
            updated=updated,
            skipped=outcome.skipped,
            warnings=outcome.warnings,
            conflicts=conflicts,
        )

    # -- reads / deletes ---------------------------------------------------
    def list_events(
        self, user_id: int, *, start: date | None = None, end: date | None = None
    ) -> list[ScheduleEvent]:
        if start is not None and end is not None and start > end:
            raise DomainValidationError("'from' must not be after 'to'")
        if start is not None and end is not None:
            return self._events.list_range(user_id, start, end)
        if start is not None:
            return self._events.list_range(user_id, start, date.max)
        if end is not None:
            return self._events.list_range(user_id, date.min, end)
        return self._events.list_by_user(user_id)

    def delete_event(self, user_id: int, event_id: int) -> None:
        if not self._events.soft_delete(event_id, user_id=user_id):
            raise NotFoundError("schedule event not found")
        self._session.commit()

    # -- conflict reporting ------------------------------------------------
    def _conflicts(
        self, user_id: int, rows: list[ParsedRow]
    ) -> list[str]:
        conflicts: list[str] = []

        # (1) Overlap inside the imported file.
        for index, left in enumerate(rows):
            for right in rows[index + 1 :]:
                if events_overlap(left.event, right.event):
                    conflicts.append(
                        f"{_label(left)} overlaps {_label(right)}"
                    )
                if len(conflicts) >= MAX_CONFLICTS:
                    return conflicts

        # (2) Overlap with the tasks of the current plan (reported, not blocked).
        tasks = self._current_plan_tasks(user_id)
        for row in rows:
            for task in tasks:
                if not (
                    task.scheduled_date
                    and task.start_time
                    and task.end_time
                    and event_occurs_on(row.event, task.scheduled_date)
                    and time_overlap(
                        row.event.start_time,
                        row.event.end_time,
                        task.start_time,
                        task.end_time,
                    )
                ):
                    continue
                conflicts.append(
                    f"{_label(row)} overlaps plan task '{task.title}' on "
                    f"{task.scheduled_date.isoformat()} "
                    f"[{task.start_time.strftime('%H:%M')}, "
                    f"{task.end_time.strftime('%H:%M')}]"
                )
                if len(conflicts) >= MAX_CONFLICTS:
                    return conflicts
        return conflicts

    def _current_plan_tasks(self, user_id: int) -> list[Task]:
        plan = self._plans.get_latest_by_user(user_id)
        if plan is None or plan.id is None:
            return []
        if getattr(plan.status, "value", plan.status) != "active":
            return []
        tasks = self._tasks.list_by_plan(plan.id)
        return [
            task
            for task in tasks
            if task.status not in {TaskStatus.COMPLETED, TaskStatus.SKIPPED}
        ]


def _label(row: ParsedRow) -> str:
    return f"row {row.row_number} '{row.event.title}'"


__all__ = ["MAX_CONFLICTS", "ScheduleEventService"]
