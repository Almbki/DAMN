"""Auth endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service
from app.application.services import AuthService
from app.core.config import get_settings
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.common import ErrorResponse
from app.schemas.user import UserRead

router = APIRouter()


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
) -> UserRead:
    user = service.register(
        email=str(payload.email),
        password=payload.password,
        display_name=payload.display_name,
        execution_weight=payload.execution_weight,
        profile=payload.profile,
    )
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
