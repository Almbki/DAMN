"""Auth endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_auth_service, get_db, get_profile_service
from app.application.services import AuthService, ProfileService
from app.core.config import get_settings
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.common import ErrorResponse
from app.schemas.profile import ProfileUpsert, RegisterRequestWithProfile
from app.schemas.user import UserRead

router = APIRouter()

_PROFILE_FIELDS = ("mbti_type", "mbti_dims", "identity")


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a user account. Email must be unique.",
    responses={409: {"model": ErrorResponse, "description": "Email already registered"}},
)
def register(
    payload: RegisterRequestWithProfile,
    service: AuthService = Depends(get_auth_service),
    profile_service: ProfileService = Depends(get_profile_service),
    db: Session = Depends(get_db),
) -> UserRead:
    user = service.register(
        email=str(payload.email),
        password=payload.password,
        display_name=payload.display_name,
        execution_weight=payload.execution_weight,
        profile=payload.profile,
    )
    if any(getattr(payload, field) is not None for field in _PROFILE_FIELDS):
        # The account is already committed: a profile failure must never turn a
        # successful registration into an error response.
        try:
            profile_service.upsert_profile(
                user.id or 0,
                ProfileUpsert(
                    mbti_type=payload.mbti_type,
                    mbti_dims=payload.mbti_dims,
                    identity=payload.identity,
                ),
            )
        except Exception:  # noqa: BLE001 - profile is best-effort at registration
            db.rollback()
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in and obtain a JWT access token",
    responses={401: {"model": ErrorResponse, "description": "Invalid credentials"}},
)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    user = service.authenticate(str(payload.email), payload.password)
    token = service.create_token(user)
    settings = get_settings()
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )
