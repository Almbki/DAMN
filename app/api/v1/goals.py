"""Goal endpoints (frontend: 目标 / 待拆解清单).

`status=draft` marks a not-yet-decomposed item so the frontend's goal list
survives a refresh or a device switch. Independent of the planner, which keeps
creating its own goals while generating a plan.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, get_goal_service
from app.application.dto.goal import GoalCreateData
from app.application.services import GoalService
from app.domain.models import Goal, User
from app.schemas.common import ErrorResponse
from app.schemas.goal import (
    GoalCreate,
    GoalDetailRead,
    GoalLifecycleImpact,
    GoalUpdate,
)

router = APIRouter()

_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}
_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Goal not found"}}


@router.get(
    "",
    response_model=list[GoalDetailRead],
    summary="List goals (optionally only the ones waiting to be decomposed)",
    description="Pass `?status=draft` for the frontend's 待拆解清单.",
    responses={**_AUTH},
)
def list_goals(
    status_filter: str | None = Query(default=None, alias="status"),
    include_archived: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    service: GoalService = Depends(get_goal_service),
) -> list[GoalDetailRead]:
    goals = service.list_goals(
        current_user.id or 0,
        status=status_filter,
        include_archived=include_archived,
    )
    return [GoalDetailRead.model_validate(goal) for goal in goals]


@router.post(
    "",
    response_model=GoalDetailRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a goal (or a draft item with status=draft)",
    responses={**_AUTH},
)
def create_goal(
    payload: GoalCreate,
    current_user: User = Depends(get_current_user),
    service: GoalService = Depends(get_goal_service),
) -> GoalDetailRead:
    goal: Goal = service.create(
        current_user.id or 0, GoalCreateData(**payload.model_dump())
    )
    return GoalDetailRead.model_validate(goal)


@router.patch(
    "/{goal_id}",
    response_model=GoalDetailRead,
    summary="Edit a goal (title / description / status / deadline / priority)",
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    current_user: User = Depends(get_current_user),
    service: GoalService = Depends(get_goal_service),
) -> GoalDetailRead:
    goal = service.update(
        current_user.id or 0, goal_id, payload.model_dump(exclude_unset=True)
    )
    return GoalDetailRead.model_validate(goal)


@router.post(
    "/{goal_id}/archive",
    response_model=GoalLifecycleImpact,
    response_model_exclude_none=True,
    summary="Archive a goal and remove its unfinished tasks from the active plan",
    description=(
        "Completed tasks and their execution history are preserved. The goal "
        "can be restored later."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def archive_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    service: GoalService = Depends(get_goal_service),
) -> GoalLifecycleImpact:
    impact = service.archive(current_user.id or 0, goal_id)
    return GoalLifecycleImpact(
        goal_id=impact["goal_id"],
        removed_tasks=impact["removed_tasks"],
        preserved_completed_tasks=impact["preserved_completed_tasks"],
    )


@router.post(
    "/{goal_id}/restore",
    response_model=GoalLifecycleImpact,
    summary="Restore an archived goal and its previously archived tasks",
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def restore_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    service: GoalService = Depends(get_goal_service),
) -> GoalLifecycleImpact:
    restored = service.restore(current_user.id or 0, goal_id)
    return GoalLifecycleImpact(
        goal_id=goal_id,
        removed_tasks=0,
        preserved_completed_tasks=0,
        restored_tasks=restored,
    )


@router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a goal",
    description="204 on success. 409 when a plan task still references the goal.",
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    service: GoalService = Depends(get_goal_service),
) -> None:
    service.delete(current_user.id or 0, goal_id)
