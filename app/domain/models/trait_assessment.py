"""TraitAssessment domain entity.

Minimal resumable Level 1 CAT session state: the ordered administered responses,
the round-robin cursor, and the artifact identity. The posterior/theta values are
never stored - they are replayed by ``Level1Runtime``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow


class TraitAssessment(DomainModel):
    id: str
    user_id: int
    status: str = "in_progress"  # in_progress | completed | abandoned
    responses: list[dict[str, Any]] = Field(default_factory=list)
    rr_index: int = 0
    unavailable: list[str] = Field(default_factory=list)
    current_item_id: str | None = None
    model_version: str = ""
    calibration_version: str = ""
    artifact_hash: str = ""
    feature_version: str = ""
    trait_profile: dict[str, Any] | None = None
    #: real | synthetic - synthetic Level 1 seeds are identifiable.
    data_origin: str = "real"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None


__all__ = ["TraitAssessment"]