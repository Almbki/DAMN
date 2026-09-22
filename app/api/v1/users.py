"""User endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    get_auth_service,
    get_current_user,
    get_profile_service,
    get_situation_service,
)
from app.application.exceptions import NotFoundError
from app.application.services import AuthService, ProfileService, SituationService
from app.domain.models import User
from app.schemas.common import ErrorResponse
from app.schemas.profile import ProfileRead
from app.schemas.user import (
    SchedulingPreferences,
    SituationTrendRead,
    UserRead,
    UserUpdate,
)

router = APIRouter()

_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}

#: Fields handled by ProfileService (dedicated columns + state reset).
PORTRAIT_FIELDS = frozenset({"mbti_type", "mbti_dims", "identity"})


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
    profiles: ProfileService = Depends(get_profile_service),
) -> UserRead:
    user_id = current_user.id or 0
    updated = service.update_user(
        user_id,
        display_name=payload.display_name,
        execution_weight=payload.execution_weight,
        profile=payload.profile,
    )
    # Portrait fields are handled separately: they live on dedicated columns and
    # changing them re-initialises the adaptive state. Only fields the client
    # actually sent are touched (an explicit null clears one).
    provided = PORTRAIT_FIELDS & payload.model_fields_set
    if provided:
        profiles.upsert_profile(
            user_id,
            provided=set(provided),
            mbti_type=payload.mbti_type,
            mbti_dims=payload.mbti_dims,
            identity=payload.identity,
        )
        updated = service.get_user(user_id)
    return UserRead.model_validate(updated)


@router.get(
    "/me/profile",
    response_model=ProfileRead,
    summary="Read the user portrait (static MBTI + adaptive state)",
    description=(
        "404 when the user has not set a portrait yet. `degraded` is true while "
        "`update_count < 3`: the numbers are then cold-start priors derived from "
        "the MBTI template, not a psychological assessment."
    ),
    responses={**_AUTH, 404: {"model": ErrorResponse, "description": "Profile not set"}},
)
def read_profile(
    current_user: User = Depends(get_current_user),
    profiles: ProfileService = Depends(get_profile_service),
) -> ProfileRead:
    user_id = current_user.id or 0
    if not profiles.is_configured(user_id):
        raise NotFoundError("profile not set")
    return ProfileRead.from_parts(profiles.get_profile(user_id), profiles.get_state(user_id))


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
