"""ML layer: predictor interfaces + first-version statistical implementations.

The Service layer depends only on the ``Protocol`` interfaces declared here
(``app/ml/base.py``). Concrete implementations live next to them and can be
swapped for LightGBM / XGBoost / sklearn / PyTorch without touching the
Service or API layers.
"""

from app.ml.base import (
    CompletionPrediction,
    CompletionPredictor,
    DurationPrediction,
    DurationPredictor,
    PredictionRequest,
    StressPrediction,
    StressPredictor,
    TaskFeatureSet,
    TimeSlotPrediction,
    TimeSlotPredictor,
    UserFeatureSet,
)

__all__ = [
    "CompletionPrediction",
    "CompletionPredictor",
    "DurationPrediction",
    "DurationPredictor",
    "PredictionRequest",
    "StressPrediction",
    "StressPredictor",
    "TaskFeatureSet",
    "TimeSlotPrediction",
    "TimeSlotPredictor",
    "UserFeatureSet",
]
