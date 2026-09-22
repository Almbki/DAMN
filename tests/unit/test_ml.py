"""Unit tests for the statistical (mock) ML predictors and user-model builder.

These assertions document the *statistical* behaviour of the first version -
they are NOT asserting trained-model quality.
"""

from __future__ import annotations

from app.domain.models.enums import CognitiveLoad, Priority, TimeOfDay
from app.ml.base import PredictionRequest, TaskFeatureSet, UserFeatureSet
from app.ml.completion_predictor import StatisticalCompletionPredictor
from app.ml.duration_predictor import StatisticalDurationPredictor
from app.ml.predictors import PredictorSet
from app.ml.stress_predictor import StatisticalStressPredictor
from app.ml.time_predictor import StatisticalTimeSlotPredictor


def _task(**overrides) -> TaskFeatureSet:
    base = dict(
        task_id=1,
        title="Math practice",
        estimated_duration_minutes=60,
        cognitive_load=CognitiveLoad.MEDIUM,
        priority=Priority.MEDIUM,
    )
    base.update(overrides)
    return TaskFeatureSet(**base)


def _user(**overrides) -> UserFeatureSet:
    base = dict(
        user_id=1,
        duration_factor=1.5,
        completion_rate_7d=0.8,
        completion_rate_30d=0.7,
        avg_stress=4.0,
        avg_energy=6.0,
        sample_size=10,
    )
    base.update(overrides)
    return UserFeatureSet(**base)


def test_duration_predictor_applies_factor() -> None:
    request = PredictionRequest(task=_task(), user=_user(duration_factor=1.5))
    prediction = StatisticalDurationPredictor().predict(request)
    assert prediction.theoretical_minutes == 60
    assert prediction.predicted_minutes == 90
    assert prediction.source.startswith("mock")


def test_duration_predictor_penalises_high_cognitive_load() -> None:
    base = StatisticalDurationPredictor()
    medium = base.predict(PredictionRequest(task=_task(), user=_user()))
    high = base.predict(
        PredictionRequest(task=_task(cognitive_load=CognitiveLoad.HIGH), user=_user())
    )
    assert high.predicted_minutes > medium.predicted_minutes


def test_completion_predictor_returns_probability() -> None:
    prediction = StatisticalCompletionPredictor().predict(
        PredictionRequest(task=_task(), user=_user())
    )
    assert 0.0 <= prediction.probability <= 1.0
    assert prediction.confidence > 0


def test_completion_predictor_penalises_high_stress() -> None:
    predictor = StatisticalCompletionPredictor()
    calm = predictor.predict(PredictionRequest(task=_task(), user=_user(avg_stress=2.0)))
    stressed = predictor.predict(PredictionRequest(task=_task(), user=_user(avg_stress=9.0)))
    assert stressed.probability < calm.probability


def test_stress_predictor_flags_overload() -> None:
    prediction = StatisticalStressPredictor().predict(
        PredictionRequest(
            task=_task(cognitive_load=CognitiveLoad.HIGH),
            user=_user(avg_stress=8.0),
        )
    )
    assert prediction.predicted_stress >= 8.0
    assert prediction.should_reduce_load is True


def test_time_slot_predictor_uses_preference() -> None:
    prediction = StatisticalTimeSlotPredictor().predict(
        PredictionRequest(
            task=_task(cognitive_load=CognitiveLoad.HIGH),
            user=_user(preferred_time_slots={"high": "evening"}),
        )
    )
    assert prediction.recommended_slot == TimeOfDay.EVENING


def test_predictor_set_default_wires_all_four() -> None:
    predictors = PredictorSet.default()
    assert predictors.duration.name.startswith("statistical")
    assert predictors.completion.name.startswith("statistical")
    assert predictors.stress.name.startswith("statistical")
    assert predictors.time_slot.name.startswith("statistical")
