"""Auth endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service, get_profile_service
from app.application.services import AuthService, ProfileService
from app.core.config import get_settings
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.common import ErrorResponse
from app.schemas.user import UserRead

router = APIRouter()

#: Portrait fields handled by ProfileService on registration.
PORTRAIT_FIELDS = frozenset({"mbti_type", "mbti_dims", "identity"})


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a user account. Email must be unique.",
    responses={409: {"model": ErrorResponse, "description": "Email already registered"}},
)
def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
    profiles: ProfileService = Depends(get_profile_service),
) -> UserRead:
    user = service.register(
        email=str(payload.email),
        password=payload.password,
        display_name=payload.display_name,
        execution_weight=payload.execution_weight,
        profile=payload.profile,
    )
    # A portrait supplied at sign-up seeds the adaptive state immediately.
    provided = {field for field in PORTRAIT_FIELDS if field in payload.model_fields_set}
    if provided and user.id is not None:
        profiles.upsert_profile(
            user.id,
            provided=provided,
            mbti_type=payload.mbti_type,
            mbti_dims=payload.mbti_dims,
            identity=payload.identity,
        )
        user = service.get_user(user.id)
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
