"""Course / timetable import and fixed-event listing."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.deps import get_current_user, get_schedule_event_service
from app.application.services import ScheduleEventService
from app.domain.models import User
from app.schemas.common import ErrorResponse
from app.schemas.schedule_event import ScheduleEventRead, ScheduleImportResult

router = APIRouter()

_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}
_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Schedule event not found"}}


@router.post(
    "/import",
    response_model=ScheduleImportResult,
    summary="Import a CSV/XLSX timetable",
    description=(
        "Tolerantly imports a course/work timetable. Accepts `.csv` and `.xlsx` "
        "(legacy `.xls` is rejected), max 2 MB / 1000 rows. Chinese and English "
        "headers are both accepted; invalid rows are skipped with warnings. "
        "Use `?dry_run=true` to validate without storing anything. The import "
        "reports conflicts with other imported events and with the current "
        "plan's tasks but never blocks on them."
    ),
    responses={
        **_AUTH,
        422: {"model": ErrorResponse, "description": "Invalid file / too large"},
    },
)
def import_schedule(
    file: UploadFile = File(..., description="Timetable .csv or .xlsx"),
    dry_run: bool = Query(default=False, description="Parse only, do not store"),
    term_start: date | None = Query(
        default=None,
        description=(
            "Term start date (YYYY-MM-DD) for weekly-grid XLSX files. "
            "Overrides the date parsed from the sheet's note."
        ),
    ),
    current_user: User = Depends(get_current_user),
    service: ScheduleEventService = Depends(get_schedule_event_service),
) -> ScheduleImportResult:
    content = file.file.read()
    result = service.import_file(
        current_user.id or 0,
        filename=file.filename or "",
        content=content,
        dry_run=dry_run,
        term_start=term_start,
    )
    return ScheduleImportResult(**result.model_dump())


@router.get(
    "",
    response_model=list[ScheduleEventRead],
    summary="List imported schedule events",
    description=(
        "`?from=YYYY-MM-DD&to=YYYY-MM-DD` keeps events that can occur inside "
        "the range (weekly recurrences included)."
    ),
    responses={**_AUTH},
)
def list_schedules(
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: ScheduleEventService = Depends(get_schedule_event_service),
) -> list[ScheduleEventRead]:
    events = service.list_events(current_user.id or 0, start=from_, end=to)
    return [ScheduleEventRead.model_validate(event) for event in events]


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an imported schedule event",
    responses={**_AUTH, **_NOT_FOUND},
)
def delete_schedule(
    event_id: int,
    current_user: User = Depends(get_current_user),
    service: ScheduleEventService = Depends(get_schedule_event_service),
) -> None:
    service.delete_event(current_user.id or 0, event_id)


__all__ = ["router"]
