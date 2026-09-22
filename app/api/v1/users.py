"""User endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_auth_service, get_current_user, get_situation_service
from app.application.services import AuthService, SituationService
from app.domain.models import User
from app.schemas.common import ErrorResponse
from app.schemas.user import (
    SchedulingPreferences,
    SituationTrendRead,
    UserRead,
    UserUpdate,
)

router = APIRouter()


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the current user",
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get(
    "/me/situation/trends",
    response_model=SituationTrendRead,
    summary="Energy / stress / efficacy trend for the profile page",
    description=(
        "Daily points over the last `days` (2-90, default 14). Days without a "
        "check-in have `null` values. `samples`/`min_samples`/`sufficient` say "
        "whether the history is enough to trust the curve; `drivers` explains "
        "the reasoning in plain language."
    ),
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def read_situation_trends(
    days: int = Query(default=14, ge=2, le=90),
    current_user: User = Depends(get_current_user),
    service: SituationService = Depends(get_situation_service),
) -> SituationTrendRead:
    return service.get_trends(current_user.id or 0, days=days)


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update the current user profile",
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserRead:
    updated = service.update_user(
        current_user.id or 0,
        display_name=payload.display_name,
        execution_weight=payload.execution_weight,
        profile=payload.profile,
    )
    return UserRead.model_validate(updated)


@router.get(
    "/me/preferences",
    response_model=SchedulingPreferences,
    summary="Read the scheduling preferences in effect",
    description=(
        "Effective values: the dedicated preferences column, falling back to "
        "legacy `profile` keys, then defaults. This is what plan generation uses "
        "when the request omits the four caps."
    ),
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def read_preferences(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> SchedulingPreferences:
    return SchedulingPreferences.model_validate(
        service.get_preferences(current_user.id or 0)
    )


@router.put(
    "/me/preferences",
    response_model=SchedulingPreferences,
    summary="Replace the scheduling preferences",
    description=(
        "Full overwrite (the frontend merges before submitting). Stored on a "
        "dedicated column so `PATCH /users/me` (wholesale `profile`) cannot wipe "
        "them. `POST /plans/generate` falls back to these when a cap is omitted."
    ),
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def update_preferences(
    payload: SchedulingPreferences,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> SchedulingPreferences:
    updated = service.update_preferences(
        current_user.id or 0, payload.model_dump(mode="json")
    )
    return SchedulingPreferences.model_validate(updated)
