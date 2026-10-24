"""Three-layer user model runtime.

Level 1 (trait) -> Level 2 (daily state) -> Level 3 (task outcome prediction).

This package is a **sidecar** like ``app/agent``: it is imported by the
application layer, never by ``app/domain``, and it never touches a database or
FastAPI. Level 3 runs in shadow mode by default and its output is never a
control signal for the scheduler or the rule engine.
"""

from app.user_models.contracts import (
    DynamicStateSnapshot,
    HistoryBundle,
    Level3Mode,
    Level3Prediction,
    ModelLevel,
    ModelMetadata,
    ModelStatus,
    StateEstimate,
    TaskPredictionContext,
    TraitDomain,
    TraitSnapshot,
    UserModelContext,
)
from app.user_models.runtime import UserModelRuntime
from app.user_models.shadow import Level3ShadowRunner, ShadowPredictionRecord

__all__ = [
    "DynamicStateSnapshot",
    "HistoryBundle",
    "Level3Mode",
    "Level3Prediction",
    "Level3ShadowRunner",
    "ModelLevel",
    "ModelMetadata",
    "ModelStatus",
    "ShadowPredictionRecord",
    "StateEstimate",
    "TaskPredictionContext",
    "TraitDomain",
    "TraitSnapshot",
    "UserModelContext",
    "UserModelRuntime",
]