"""Task endpoints (patch / delete / move / backlog / local reschedule)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status

from app.api.deps import (
    get_current_user,
    get_plan_service,
    get_task_scheduling_service,
)
from app.api.v1.mappers import task_read
from app.application.exceptions import NotFoundError
from app.application.services import PlanService, TaskSchedulingService
from app.domain.models import User
from app.domain.models.enums import TaskStatus
from app.schemas.common import ErrorResponse
from app.schemas.task import TaskMoveRequest, TaskRead, TaskUpdateRequest

router = APIRouter()

_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}
_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Task not found"}}
_CONFLICT = {
    409: {"model": ErrorResponse, "description": "Task lifecycle conflict"},
    422: {"model": ErrorResponse, "description": "Deterministic scheduling rejection"},
}


def _read_task(
    plan_service: PlanService, user_id: int, plan_id: int, task_id: int
) -> TaskRead:
    """Read one task with standards + chunk-group aggregation."""
    detail = plan_service.get_plan(user_id, plan_id)
    chunk_groups: dict[int, list] = {}
    for item in detail.tasks:
        if item.task.chunk_index is None:
            continue
        root = item.task.parent_task_id or item.task.id
        chunk_groups.setdefault(root, []).append(item.task)
    for item in detail.tasks:
        if item.task.id != task_id:
            continue
        group = (
            chunk_groups.get(item.task.parent_task_id or item.task.id)
            if item.task.chunk_index is not None
            else None
        )
        return task_read(item, group)
    raise NotFoundError("task not found in plan")


@router.patch(
    "/{plan_id}/tasks/{task_id}",
    response_model=TaskRead,
    status_code=http_status.HTTP_200_OK,
    summary="Patch a task (status, actual execution data, standards)",
    description=(
        "Updates a task and its sub-standards. Marking a task completed also "
        "records a TaskExecution row - the raw data asset used to train the "
        "duration / completion / stress predictors later. Placement edits "
        "(date/start/end) go through the same deterministic scheduling "
        "validation as drag-and-drop MOVE."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}, **_CONFLICT},
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
    return _read_task(plan_service, current_user.id or 0, plan_id, task.id or task_id)


@router.post(
    "/{plan_id}/tasks/{task_id}/backlog",
    response_model=TaskRead,
    status_code=http_status.HTTP_200_OK,
    summary="Move a task into the backlog (clear placement, keep identity)",
    description=(
        "Keeps the task row, goal, work-unit/chunk identity and duration, but "
        "clears scheduled_date/start_time/end_time and sets status=backlog. "
        "Idempotent. Recurring occurrences, completed/skipped/missed tasks and "
        "non-active plan versions are rejected."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}, **_CONFLICT},
)
def move_task_to_backlog(
    plan_id: int,
    task_id: int,
    current_user: User = Depends(get_current_user),
    scheduling: TaskSchedulingService = Depends(get_task_scheduling_service),
    plan_service: PlanService = Depends(get_plan_service),
) -> TaskRead:
    scheduling.move_task_to_backlog(current_user.id or 0, plan_id, task_id)
    return _read_task(plan_service, current_user.id or 0, plan_id, task_id)


@router.post(
    "/{plan_id}/tasks/{task_id}/move",
    response_model=TaskRead,
    status_code=http_status.HTTP_200_OK,
    summary="Move one task to a target date/time (30-minute grid)",
    description=(
        "Deterministic execution-time MOVE. The start is snapped to the nearest "
        "30 minutes (half-up) and the placement is validated by the same "
        "RuleEngine/scheduler constraints as task detail edits: fixed events, "
        "daily/available capacity, buffer, cognitive limits, per-goal cap, "
        "earliest date, deadline and recurrence day. Never calls an LLM and "
        "never triggers a replan."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}, **_CONFLICT},
)
def move_task(
    plan_id: int,
    task_id: int,
    payload: TaskMoveRequest,
    current_user: User = Depends(get_current_user),
    scheduling: TaskSchedulingService = Depends(get_task_scheduling_service),
    plan_service: PlanService = Depends(get_plan_service),
) -> TaskRead:
    scheduling.move_task(
        current_user.id or 0,
        plan_id,
        task_id,
        target_date=payload.target_date,
        target_start=payload.target_start,
    )
    return _read_task(plan_service, current_user.id or 0, plan_id, task_id)


@router.post(
    "/{plan_id}/tasks/{task_id}/local-reschedule",
    response_model=list[TaskRead],
    status_code=http_status.HTTP_200_OK,
    summary="Shift a work-unit sequence from this task onward",
    description=(
        "Releases only the selected task and its later unfinished tasks in the "
        "same project series, then re-places them with the deterministic "
        "scheduler from today. Completed/skipped/missed tasks and unrelated "
        "goals are frozen. Atomic: any infeasible placement rolls the whole "
        "operation back with LOCAL_RESCHEDULE_INFEASIBLE. Never calls an LLM "
        "and never triggers FULL_REPLAN."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}, **_CONFLICT},
)
def local_reschedule(
    plan_id: int,
    task_id: int,
    current_user: User = Depends(get_current_user),
    scheduling: TaskSchedulingService = Depends(get_task_scheduling_service),
    plan_service: PlanService = Depends(get_plan_service),
) -> list[TaskRead]:
    user_id = current_user.id or 0
    updated = scheduling.local_reschedule(user_id, plan_id, task_id)
    return [
        _read_task(plan_service, user_id, plan_id, item.id or task_id)
        for item in updated
        if item.id is not None
    ]


@router.get(
    "/{plan_id}/backlog",
    response_model=list[TaskRead],
    status_code=http_status.HTTP_200_OK,
    summary="List the plan's backlog tasks",
    description=(
        "Backend-authoritative backlog: tasks with status=backlog. Clients must "
        "not infer backlog from a null scheduled_date."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def list_backlog(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
) -> list[TaskRead]:
    user_id = current_user.id or 0
    detail = plan_service.get_plan(user_id, plan_id)
    return [
        task_read(item)
        for item in detail.tasks
        if item.task.status == TaskStatus.BACKLOG
    ]


@router.delete(
    "/{plan_id}/tasks/{task_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a task (or a whole recurring series)",
    description=(
        "Marks the task as deleted without removing the row, so its "
        "TaskExecution history (ML training data) and TaskStandard rows are "
        "preserved. Deleted tasks disappear from plan reads, insights and plan "
        "change diffs. Idempotent: deleting it again still returns 204. "
        "`?scope=series` soft-deletes every unfinished occurrence of the same "
        "series in this plan version; completed occurrences survive. A "
        "non-series task rejects `scope=series` with 422."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def delete_task(
    plan_id: int,
    task_id: int,
    reason: str | None = Query(default=None, max_length=255),
    scope: Literal["single", "series"] = Query(default="single"),
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
) -> None:
    if scope == "series":
        plan_service.delete_task_series(
            current_user.id or 0, plan_id, task_id, reason=reason
        )
        return
    plan_service.delete_task(
        current_user.id or 0, plan_id, task_id, reason=reason
    )
