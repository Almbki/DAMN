"""User domain entity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, EmailStr, Field

from app.domain.models.base import DomainModel, utcnow


class User(DomainModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int | None = None
    email: EmailStr
    password_hash: str
    display_name: str | None = None
    # Optional self reported "execution ability" weight (0..1), used as a
    # prior by the user-model / ML layer before real history exists.
    execution_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    # Free-form profile: available hours, sleep schedule, preferences, ...
    profile: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
