"""Statistical (mock) stress predictor.

Simple statistics, NOT a trained ML model: predicted stress is the user's
average stress shifted by a per-load delta, mapped to a ``LoadLevel`` and a
"reduce load" flag. Marked ``source="mock:statistical"``; replaceable via the
:class:`~app.ml.base.StressPredictor` Protocol.
"""

from __future__ import annotations

from app.domain.models.enums import CognitiveLoad, LoadLevel
from app.ml.base import PredictionRequest, StressPrediction

#: Stress shift per cognitive-load bucket.
_LOAD_DELTA = {
    CognitiveLoad.HIGH: 2.0,
    CognitiveLoad.MEDIUM: 1.0,
    CognitiveLoad.LOW: 0.0,
    CognitiveLoad.RESTORATIVE: -1.0,
}


def _load_level(value: float) -> LoadLevel:
    if value < 3:
        return LoadLevel.LOW
    if value < 6:
        return LoadLevel.MODERATE
    if value < 8:
        return LoadLevel.HIGH
    return LoadLevel.OVERLOADED


class StatisticalStressPredictor:
    """Heuristic stress predictor.

    Mock / placeholder implementation.

    .. note::
        This is a hand-written formula, not a trained ML model. It is simple,
        deterministic and fully replaceable via the ``StressPredictor``
        Protocol.
    """

    name = "statistical-stress-v0"
    source = "mock:statistical"

    def predict(self, request: PredictionRequest) -> StressPrediction:
        """``predicted_stress = avg_stress + delta`` clamped to ``[0, 10]``.

        ``should_reduce_load`` when ``predicted_stress >= 7`` or the delta is
        ``>= 2``.
        """
        task = request.task
        user = request.user

        delta = _LOAD_DELTA.get(task.cognitive_load, 0.0)
        predicted_stress = min(10.0, max(0.0, user.avg_stress + delta))
        should_reduce_load = predicted_stress >= 7 or (
            predicted_stress - user.avg_stress >= 2
        )
        confidence = min(0.3 + user.sample_size / 60.0, 0.8)

        return StressPrediction(
            predicted_stress=round(predicted_stress, 4),
            predicted_load_level=_load_level(predicted_stress),
            should_reduce_load=should_reduce_load,
            confidence=round(confidence, 4),
            source=self.source,
        )