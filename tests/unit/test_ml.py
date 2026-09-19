"""Unit tests for the statistical (mock) ML predictors and user-model builder.

These assertions document the *statistical* behaviour of the first version -
they are NOT asserting trained-model quality.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.models import Feedback, TaskExecution
from app.domain.models.enums import CognitiveLoad, Priority, TimeOfDay
from app.ml.base import PredictionRequest, TaskFeatureSet, UserFeatureSet
from app.ml.completion_predictor import StatisticalCompletionPredictor
from app.ml.duration_predictor import StatisticalDurationPredictor
from app.ml.predictors import PredictorSet
from app.ml.stress_predictor import StatisticalStressPredictor
from app.ml.time_predictor import StatisticalTimeSlotPredictor
from app.ml.user_model import StatisticalUserModelBuilder


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


def test_user_model_builder_derives_duration_factor() -> None:
    now = datetime.now(UTC)
    executions = [
        TaskExecution(
            task_id=i,
            user_id=1,
            planned_duration=60,
            actual_duration=90,
            completion_rate=1.0,
            completed=True,
            time_of_day=TimeOfDay.MORNING,
            created_at=now - timedelta(days=1),
        )
        for i in range(1, 5)
    ]
    model = StatisticalUserModelBuilder().build(
        executions,
        [],
        user_id=1,
        task_loads={i: CognitiveLoad.HIGH for i in range(1, 5)},
    )
    assert model.sample_size == 4
    assert model.duration_factors["high"] == round(1.5, 3) or model.duration_factors["high"] > 1.0
    assert model.preferred_time_slots["high"] == "morning"


def test_user_model_builder_features_from_feedback() -> None:
    now = datetime.now(UTC)
    feedback = [
        Feedback(
            user_id=1,
            plan_id=1,
            date=(now - timedelta(days=1)).date(),
            completion_rate=0.5,
            stress_level=7,
            energy_level=3,
            sleep_hours=6.0,
        )
    ]
    features = StatisticalUserModelBuilder().to_features(
        None, [], feedback, user_id=1, execution_weight=0.4
    )
    assert features.avg_stress == 7.0
    assert features.avg_energy == 3.0
    assert features.sleep_hours == 6.0
    assert features.sample_size == 0
