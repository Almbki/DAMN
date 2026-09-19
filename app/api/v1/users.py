"""User endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service, get_current_user
from app.application.services import AuthService
from app.domain.models import User
from app.schemas.common import ErrorResponse
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the current user",
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


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
