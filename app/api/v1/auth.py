"""Auth endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_auth_service,
    get_execution_reconciliation_service,
    get_profile_service,
)
from app.application.services import (
    AuthService,
    ExecutionReconciliationService,
    ProfileService,
)
from app.core.config import get_settings
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.common import ErrorResponse
from app.schemas.user import UserRead

router = APIRouter()
logger = logging.getLogger(__name__)

#: Portrait fields handled by ProfileService on registration.
PORTRAIT_FIELDS = frozenset({"identity"})


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
    reconciliation: ExecutionReconciliationService = Depends(
        get_execution_reconciliation_service
    ),
) -> TokenResponse:
    user = service.authenticate(str(payload.email), payload.password)
    # Day-boundary settlement happens on login too, so a user who has not opened
    # the app for several days still sees OVERDUE / MISSED / PENDING_FEEDBACK.
    # Best-effort: a lifecycle failure must never block authentication.
    if user.id is not None:
        try:
            reconciliation.reconcile_user_execution_state(user.id)
        except Exception as exc:  # noqa: BLE001 - auth must stay available
            logger.warning(
                "execution reconciliation failed on login for user=%s: %s: %s",
                user.id,
                type(exc).__name__,
                exc,
            )
    token = service.create_token(user)
    settings = get_settings()
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )
