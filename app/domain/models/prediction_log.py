"""PredictionLog domain entity - what a predictor said, so it can be scored.

Without this table there is no way to answer "is the model any good?": the
predicted value must be recorded next to the later observed actual value
(``task_executions``) with the model version and a feature fingerprint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow


class PredictionLog(DomainModel):
    id: int | None = None
    user_id: int
    plan_id: int | None = None
    #: Null for plan-level predictions (e.g. the adjustment route).
    task_id: int | None = None
    model_name: str
    model_version: str = ""
    #: duration | completion | stress | time_slot | adjustment
    prediction_type: str
    #: Stable hash of the feature vector, for drift analysis / debugging.
    feature_hash: str = ""
    #: The prediction itself (e.g. {"predicted_minutes": 138}).
    predicted: dict[str, Any] = Field(default_factory=dict)
    #: Truthful origin: mock:statistical | fallback:rule | llm | xgboost-v1 ...
    source: str = ""
    created_at: datetime = Field(default_factory=utcnow)
