"""Statistical (mock) duration predictor.

Simple statistics, NOT a trained ML model: the predicted duration is the
theoretical estimate scaled by a per-user ``duration_factor`` with small
hand-tuned adjustments for cognitive load and difficulty. Marked
``source="mock:statistical"`` so the API is honest about provenance; the
:class:`~app.ml.base.DurationPredictor` Protocol makes this implementation
replaceable by a real trained model later.
"""

from __future__ import annotations

from app.domain.models.enums import CognitiveLoad
from app.ml.base import DurationPrediction, PredictionRequest


class StatisticalDurationPredictor:
    """Heuristic duration predictor.

    Mock / placeholder implementation.

    .. note::
        This is a hand-written formula, not a trained ML model. It is simple,
        deterministic and fully replaceable via the ``DurationPredictor``
        Protocol.
    """

    name = "statistical-duration-v0"
    source = "mock:statistical"

    def predict(self, request: PredictionRequest) -> DurationPrediction:
        """``predicted = round(estimated * factor)`` with adjustments.

        * base factor = ``user.duration_factor``;
        * ``+0.15`` when the task is HIGH cognitive load;
        * ``+0.1 * (difficulty - 3)`` when ``difficulty`` is provided;
        * clawed into ``[0.6, 3.0]``.
        """
        task = request.task
        user = request.user

        factor = user.duration_factor
        if task.cognitive_load == CognitiveLoad.HIGH:
            factor += 0.15
        if task.difficulty is not None:
            factor += 0.1 * (task.difficulty - 3)
        factor = max(0.6, min(3.0, factor))

        predicted = max(1, round(task.estimated_duration_minutes * factor))
        confidence = min(0.35 + user.sample_size / 50.0, 0.85)

        return DurationPrediction(
            theoretical_minutes=task.estimated_duration_minutes,
            predicted_minutes=predicted,
            factor=round(factor, 4),
            confidence=round(confidence, 4),
            source=self.source,
        )