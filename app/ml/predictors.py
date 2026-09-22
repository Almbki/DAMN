"""`PredictorSet` grouping the five predictors used by the agent pipeline.

Four of them are the original per-task predictors (duration / completion /
stress / time-slot). ``adjustment`` is the feedback-loop predictor that decides
``NO_CHANGE`` / ``MICRO_ADJUST`` / ``FULL_REPLAN``.

``default()`` wires the statistical + rule-based (non-trained) implementations
so the whole system runs before the real ML models exist. Replace any member by
constructing the set explicitly - nothing else needs to change.
"""

from __future__ import annotations

from app.ml.adjustment import RuleBasedAdjustmentPredictor
from app.ml.base import (
    AdjustmentPredictor,
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
    """Grouping of the predictors consumed by the planning pipeline."""

    def __init__(
        self,
        duration: DurationPredictor,
        completion: CompletionPredictor,
        stress: StressPredictor,
        time_slot: TimeSlotPredictor,
        adjustment: AdjustmentPredictor | None = None,
    ) -> None:
        self.duration = duration
        self.completion = completion
        self.stress = stress
        self.time_slot = time_slot
        # Deterministic rule fallback unless the ML team injects a real model.
        self.adjustment: AdjustmentPredictor = (
            adjustment if adjustment is not None else RuleBasedAdjustmentPredictor()
        )

    @classmethod
    def default(cls) -> PredictorSet:
        """Build the first-version statistical + fallback predictor set."""
        return cls(
            duration=StatisticalDurationPredictor(),
            completion=StatisticalCompletionPredictor(),
            stress=StatisticalStressPredictor(),
            time_slot=StatisticalTimeSlotPredictor(),
            adjustment=RuleBasedAdjustmentPredictor(),
        )
