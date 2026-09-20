"""User API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str | None = None
    execution_weight: float = 0.5
    profile: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: str | None = None
    execution_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    profile: dict[str, Any] | None = None
