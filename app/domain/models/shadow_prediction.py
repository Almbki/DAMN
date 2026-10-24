"""ShadowPrediction domain entity.

One auditable Level 3 shadow inference. This row is **never** read back as a
production control signal; it exists for evaluation, disagreement analysis and
debugging.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow


class ShadowPrediction(DomainModel):
    id: int | None = None
    user_id: int
    plan_id: int | None = None
    task_id: int | None = None
    inference_timestamp: datetime = Field(default_factory=utcnow)
    model_level: str = "level3"
    model_version: str = ""
    artifact_hash: str = ""
    artifact_version: str = ""
    feature_version: str = ""
    input_hash: str = ""
    #: Small auditable digest (versions, support counts) - never raw prompts.
    input_summary: dict[str, Any] = Field(default_factory=dict)
    production_decision: dict[str, Any] = Field(default_factory=dict)
    shadow_prediction: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
    uncertainty: float | None = None
    disagreement: float | None = None
    latency_ms: int = 0
    success: bool = True
    failure_reason: str | None = None
    degraded: bool = False
    mode: str = "shadow"
    #: real | synthetic - synthetic shadow rows are demo/evaluation only.
    data_origin: str = "real"
    created_at: datetime = Field(default_factory=utcnow)