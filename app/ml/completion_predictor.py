"""Statistical (mock) completion predictor.

Simple statistics, NOT a trained ML model: a blended historical completion
rate with hand-tuned penalties for low energy, high stress, over-length tasks
and high cognitive load. Marked ``source="mock:statistical"``; replaceable via
the :class:`~app.ml.base.CompletionPredictor` Protocol.
"""

from __future__ import annotations

from app.domain.models.enums import CognitiveLoad
from app.ml.base import (
    CompletionPrediction,
    PredictionRequest,
)


class StatisticalCompletionPredictor:
    """Heuristic completion-probability predictor.

    Mock / placeholder implementation.

    .. note::
        This is a hand-written formula, not a trained ML model. It is simple,
        deterministic and fully replaceable via the ``CompletionPredictor``
        Protocol.
    """

    name = "statistical-completion-v0"
    source = "mock:statistical"

    def predict(self, request: PredictionRequest) -> CompletionPrediction:
        """``base = 0.7 * rate_7d + 0.3 * rate_30d`` minus penalties.

        Penalties: ``avg_energy < 4`` (-0.15), ``avg_stress > 7`` (-0.15),
        predicted duration exceeding ``request.available_minutes`` when set
        (-0.2), HIGH cognitive load (-0.05). Result clamped to ``[0.05, 0.98]``.
        """
        task = request.task
        user = request.user

        base = 0.7 * user.completion_rate_7d + 0.3 * user.completion_rate_30d

        if user.avg_energy < 4:
            base -= 0.15
        if user.avg_stress > 7:
            base -= 0.15

        # Predicted duration (same mock formula as the duration predictor).
        predicted_duration = round(task.estimated_duration_minutes * user.duration_factor)
        if request.available_minutes is not None and predicted_duration > request.available_minutes:
            base -= 0.2

        if task.cognitive_load == CognitiveLoad.HIGH:
            base -= 0.05

        probability = min(0.98, max(0.05, base))
        confidence = min(0.3 + user.sample_size / 60.0, 0.8)

        return CompletionPrediction(
            probability=round(probability, 4),
            confidence=round(confidence, 4),
            source=self.source,
        )