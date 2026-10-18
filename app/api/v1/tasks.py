"""Task endpoints (patch / delete a single task)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status

from app.api.deps import get_current_user, get_plan_service
from app.api.v1.mappers import task_read
from app.application.services import PlanService
from app.domain.models import User
from app.schemas.common import ErrorResponse
from app.schemas.task import TaskRead, TaskUpdateRequest

router = APIRouter()

_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}
_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Task not found"}}


@router.patch(
    "/{plan_id}/tasks/{task_id}",
    response_model=TaskRead,
    status_code=http_status.HTTP_200_OK,
    summary="Patch a task (status, actual execution data, standards)",
    description=(
        "Updates a task and its sub-standards. Marking a task completed also "
        "records a TaskExecution row - the raw data asset used to train the "
        "duration / completion / stress predictors later."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def update_task(
    plan_id: int,
    task_id: int,
    payload: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
) -> TaskRead:
    changes = payload.model_dump(
        exclude_none=True, exclude={"standard_updates"}
    )
    standard_updates = (
        [item.model_dump() for item in payload.standard_updates]
        if payload.standard_updates
        else None
    )
    task = plan_service.update_task(
        current_user.id or 0,
        plan_id,
        task_id,
        changes=changes,
        standard_updates=standard_updates,
    )
    # Re-read with standards for a complete response.
    detail = plan_service.get_plan(current_user.id or 0, plan_id)
    for item in detail.tasks:
        if item.task.id == task.id:
            return task_read(item)
    return TaskRead.model_validate(task)


@router.delete(
    "/{plan_id}/tasks/{task_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a task",
    description=(
        "Marks the task as deleted without removing the row, so its "
        "TaskExecution history (ML training data) and TaskStandard rows are "
        "preserved. Deleted tasks disappear from plan reads, insights and plan "
        "change diffs. Idempotent: deleting it again still returns 204."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def delete_task(
    plan_id: int,
    task_id: int,
    reason: str | None = Query(default=None, max_length=255),
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
) -> None:
    plan_service.delete_task(
        current_user.id or 0, plan_id, task_id, reason=reason
    )
