"""Goal-set endpoints (目标集)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, get_goal_set_service
from app.application.services import GoalSetService
from app.domain.models import User
from app.schemas.common import ErrorResponse
from app.schemas.goal import GoalDetailRead
from app.schemas.goal_set import (
    GoalSetAttachRead,
    GoalSetAttachRequest,
    GoalSetCreate,
    GoalSetDetailRead,
    GoalSetImpactRead,
    GoalSetRead,
    GoalSetRestoreRead,
    GoalSetUpdate,
)

router = APIRouter()

_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}
_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Goal set not found"}}
_FORBIDDEN = {403: {"model": ErrorResponse, "description": "Not your goal set"}}


@router.get(
    "",
    response_model=list[GoalSetRead],
    summary="List the current user's goal sets",
    responses={**_AUTH},
)
def list_goal_sets(
    include_archived: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    service: GoalSetService = Depends(get_goal_set_service),
) -> list[GoalSetRead]:
    return [
        GoalSetRead.model_validate(item)
        for item in service.list_goal_sets(
            current_user.id or 0, include_archived=include_archived
        )
    ]


@router.post(
    "",
    response_model=GoalSetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an empty goal set",
    responses={**_AUTH},
)
def create_goal_set(
    payload: GoalSetCreate,
    current_user: User = Depends(get_current_user),
    service: GoalSetService = Depends(get_goal_set_service),
) -> GoalSetRead:
    summary = service.create(
        current_user.id or 0, payload.name, payload.description
    )
    return GoalSetRead.model_validate(summary)


@router.get(
    "/{goal_set_id}",
    response_model=GoalSetDetailRead,
    summary="Get a goal set with all its goals",
    responses={**_AUTH, **_NOT_FOUND, **_FORBIDDEN},
)
def get_goal_set(
    goal_set_id: int,
    current_user: User = Depends(get_current_user),
    service: GoalSetService = Depends(get_goal_set_service),
) -> GoalSetDetailRead:
    detail = service.get_detail(current_user.id or 0, goal_set_id)
    return GoalSetDetailRead(
        **GoalSetRead.model_validate(detail).model_dump(exclude={"goals"}),
        goals=[GoalDetailRead.model_validate(goal) for goal in detail.goals],
    )


@router.patch(
    "/{goal_set_id}",
    response_model=GoalSetRead,
    summary="Rename / edit a goal set",
    responses={**_AUTH, **_NOT_FOUND, **_FORBIDDEN},
)
def update_goal_set(
    goal_set_id: int,
    payload: GoalSetUpdate,
    current_user: User = Depends(get_current_user),
    service: GoalSetService = Depends(get_goal_set_service),
) -> GoalSetRead:
    summary = service.update(
        current_user.id or 0,
        goal_set_id,
        name=payload.name,
        description=payload.description,
    )
    return GoalSetRead.model_validate(summary)


@router.post(
    "/{goal_set_id}/archive",
    response_model=GoalSetImpactRead,
    summary="Archive a goal set, its goals and their unfinished tasks",
    responses={**_AUTH, **_NOT_FOUND, **_FORBIDDEN},
)
def archive_goal_set(
    goal_set_id: int,
    current_user: User = Depends(get_current_user),
    service: GoalSetService = Depends(get_goal_set_service),
) -> GoalSetImpactRead:
    return GoalSetImpactRead.model_validate(
        service.archive(current_user.id or 0, goal_set_id)
    )


@router.post(
    "/{goal_set_id}/restore",
    response_model=GoalSetRestoreRead,
    summary="Restore a goal set and only the goals it archived",
    responses={**_AUTH, **_NOT_FOUND, **_FORBIDDEN},
)
def restore_goal_set(
    goal_set_id: int,
    current_user: User = Depends(get_current_user),
    service: GoalSetService = Depends(get_goal_set_service),
) -> GoalSetRestoreRead:
    return GoalSetRestoreRead.model_validate(
        service.restore(current_user.id or 0, goal_set_id)
    )


@router.post(
    "/{goal_set_id}/goals",
    response_model=GoalSetAttachRead,
    summary="Attach existing goals to a goal set",
    description="Idempotent: goals already in the set are ignored.",
    responses={**_AUTH, **_NOT_FOUND, **_FORBIDDEN},
)
def attach_goals(
    goal_set_id: int,
    payload: GoalSetAttachRequest,
    current_user: User = Depends(get_current_user),
    service: GoalSetService = Depends(get_goal_set_service),
) -> GoalSetAttachRead:
    return GoalSetAttachRead.model_validate(
        service.attach_goals(
            current_user.id or 0, goal_set_id, payload.goal_ids
        )
    )
