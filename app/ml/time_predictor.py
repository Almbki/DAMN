"""Statistical (mock) time-slot predictor.

Simple statistics, NOT a trained ML model: picks the user's preferred slot by
looking up ``cognitive_load`` then ``task_type`` in the user model dictionary,
falling back to a static default map. Marked ``source="mock:statistical"``;
replaceable via the :class:`~app.ml.base.TimeSlotPredictor` Protocol.
"""

from __future__ import annotations

from app.domain.models.enums import CognitiveLoad, TimeOfDay
from app.ml.base import PredictionRequest, TimeSlotPrediction

#: Static defaults used when the user model has no entry.
_DEFAULT_SLOTS = {
    CognitiveLoad.HIGH.value: TimeOfDay.MORNING.value,
    CognitiveLoad.MEDIUM.value: TimeOfDay.MORNING.value,
    CognitiveLoad.LOW.value: TimeOfDay.AFTERNOON.value,
    CognitiveLoad.RESTORATIVE.value: TimeOfDay.EVENING.value,
}

_VALID_SLOTS = {slot.value for slot in TimeOfDay}


class StatisticalTimeSlotPredictor:
    """Heuristic time-of-day predictor.

    Mock / placeholder implementation.

    .. note::
        This is a hand-written lookup, not a trained ML model. It is simple,
        deterministic and fully replaceable via the ``TimeSlotPredictor``
        Protocol.
    """

    name = "statistical-time-slot-v0"
    source = "mock:statistical"

    def predict(self, request: PredictionRequest) -> TimeSlotPrediction:
        """Recommended slot = preferred hit, else static default.

        Confidence is ``0.7`` when the user model matched
        (``cognitive_load`` or ``task_type``), ``0.5`` otherwise.
        """
        task = request.task
        user = request.user

        prefs = user.preferred_time_slots or {}
        matched = False
        slot_value = prefs.get(task.cognitive_load.value)
        if slot_value is not None:
            matched = True
        if slot_value is None and task.task_type:
            slot_value = prefs.get(task.task_type)
            if slot_value is not None:
                matched = True

        if slot_value is None:
            slot_value = _DEFAULT_SLOTS.get(task.cognitive_load.value, TimeOfDay.MORNING.value)
        if slot_value not in _VALID_SLOTS:
            slot_value = _DEFAULT_SLOTS.get(task.cognitive_load.value, TimeOfDay.MORNING.value)
            matched = False

        recommended = TimeOfDay(slot_value)
        alternatives = [
            slot for slot in TimeOfDay if slot != recommended
        ]
        confidence = 0.7 if matched else 0.5

        return TimeSlotPrediction(
            recommended_slot=recommended,
            alternatives=alternatives,
            confidence=confidence,
            source=self.source,
        )