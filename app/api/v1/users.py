"""User endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service, get_current_user, get_profile_service
from app.application.exceptions import NotFoundError
from app.application.services import AuthService, ProfileService
from app.domain.models import User
from app.schemas.common import ErrorResponse
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    ProfileUpsert,
)
from app.schemas.user import UserRead

router = APIRouter()

_PROFILE_FIELDS = ("mbti_type", "mbti_dims", "identity")


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the current user",
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get(
    "/me/profile",
    response_model=ProfileResponse,
    summary="Get the current user's adaptive profile and state",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Profile not found"},
    },
)
def read_my_profile(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    result = service.get_profile(current_user.id or 0)
    if result is None:
        raise NotFoundError("profile not found")
    return result


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update the current user profile",
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def update_me(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
    profile_service: ProfileService = Depends(get_profile_service),
) -> UserRead:
    updated = service.update_user(
        current_user.id or 0,
        display_name=payload.display_name,
        execution_weight=payload.execution_weight,
        profile=payload.profile,
    )
    user_id = current_user.id or 0
    provided = {field for field in _PROFILE_FIELDS if field in payload.model_fields_set}
    if provided:
        profile_service.upsert_profile(
            user_id,
            ProfileUpsert(
                mbti_type=payload.mbti_type,
                mbti_dims=payload.mbti_dims,
                identity=payload.identity,
            ),
            provided=provided,
        )
    return UserRead.model_validate(updated)
