"""PredictionSnapshot domain entity - frozen Level-3 inputs at prediction time."""

from __future__ import annotations

from datetime import datetime

from app.domain.models.base import DomainModel, utcnow


class PredictionSnapshot(DomainModel):
    id: int | None = None
    user_id: int
    task_id: int
    plan_id: int | None = None
    prediction_timestamp: datetime
    trait: dict | None = None
    state: dict | None = None
    task: dict | None = None
    context: dict | None = None
    history: dict | None = None
    feature_snapshot: dict | None = None
    input_hash: str = ""
    model_version: str = ""
    config_version: str = ""
    artifact_hash: str = ""
    #: shadow (this version only ever runs shadow)
    mode: str = "shadow"
    #: real | synthetic
    data_origin: str = "real"
    created_at: datetime = utcnow()


__all__ = ["PredictionSnapshot"]
