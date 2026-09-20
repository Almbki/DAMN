"""UserModel domain entity.

First version stores statistically derived factors (no trained model). The
shape is designed so a real model can later populate the same fields without
changing the Service / API layers.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow


class UserModel(DomainModel):
    id: int | None = None
    user_id: int
    model_version: str = "statistical-v0"
    # Per cognitive-load / task-type multiplier: predicted = theoretical * factor.
    duration_factors: dict[str, float] = Field(default_factory=dict)
    # Historical completion probability per cognitive-load bucket.
    completion_probability: dict[str, float] = Field(default_factory=dict)
    # Average stress delta per load level, e.g. {"high": 1.8}.
    stress_response: dict[str, float] = Field(default_factory=dict)
    # Preferred slot per task type / cognitive load, e.g. {"high": "morning"}.
    preferred_time_slots: dict[str, str] = Field(default_factory=dict)
    # Number of executions the factors were derived from (confidence proxy).
    sample_size: int = 0
    updated_at: datetime = Field(default_factory=utcnow)
