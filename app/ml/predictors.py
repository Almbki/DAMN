"""`PredictorSet` grouping the four statistical (mock) predictors."""

from __future__ import annotations

from app.ml.base import (
    CompletionPredictor,
    DurationPredictor,
    StressPredictor,
    TimeSlotPredictor,
)
from app.ml.completion_predictor import StatisticalCompletionPredictor
from app.ml.duration_predictor import StatisticalDurationPredictor
from app.ml.stress_predictor import StatisticalStressPredictor
from app.ml.time_predictor import StatisticalTimeSlotPredictor


class PredictorSet:
    """Grouping of the four predictors used by the planning pipeline.

    Concrete implementations of the ``*Predictor`` Protocols. ``default()``
    builds the statistical (mock) set - no trained models involved.
    """

    def __init__(
        self,
        duration: DurationPredictor,
        completion: CompletionPredictor,
        stress: StressPredictor,
        time_slot: TimeSlotPredictor,
    ) -> None:
        self.duration = duration
        self.completion = completion
        self.stress = stress
        self.time_slot = time_slot

    @classmethod
    def default(cls) -> PredictorSet:
        """Build the first-version statistical (mock) predictor set."""
        return cls(
            duration=StatisticalDurationPredictor(),
            completion=StatisticalCompletionPredictor(),
            stress=StatisticalStressPredictor(),
            time_slot=StatisticalTimeSlotPredictor(),
        )