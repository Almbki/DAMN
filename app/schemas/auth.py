"""Auth API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.profile import normalise_mbti_type, validate_mbti_dims


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=255)
    execution_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    profile: dict[str, Any] = Field(default_factory=dict)
    # --- optional portrait captured at sign-up (MBTI is soft, not a diagnosis) ---
    mbti_type: str | None = Field(default=None, max_length=4)
    mbti_dims: dict[str, float] | None = None
    identity: str | None = Field(default=None, max_length=200)

    _normalise_type = field_validator("mbti_type")(normalise_mbti_type)
    _validate_dims = field_validator("mbti_dims")(validate_mbti_dims)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    expires_in: int
