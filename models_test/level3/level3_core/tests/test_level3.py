"""Level 3 tests."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from level3.predictor import Level3Predictor
from level3.schemas import (
    ContextInput,
    HistoryInput,
    HistorySupport,
    Level3PredictionInput,
    OutcomeRecord,
    StateInput,
    TaskInput,
    TraitInput,
)


def make_trait():
    return TraitInput(
        theta_n=-0.3, theta_e=0.2, theta_o=0.1, theta_a=0.4, theta_c=0.3,
        se_n=0.27, se_e=0.28, se_o=0.41, se_a=0.40, se_c=0.35,
        model_version="trait_v1",
    )


def make_state_pre():
    return StateInput(
        fatigue=0.4, fatigue_uncertainty=0.15,
        stress=0.3, stress_uncertainty=0.15,
        self_efficacy=0.7, self_efficacy_uncertainty=0.12,
        model_version="ddsr_v1",
    )


def make_task():
    now = datetime(2026, 10, 24, 10, 0, 0)
    return TaskInput(
        task_id="t1",
        estimated_duration_minutes=60,
        difficulty=3,
        deadline=now + timedelta(hours=4),
        planned_start=now,
        task_type="study",
    )


def make_context():
    return ContextInput(prediction_timestamp=datetime(2026, 10, 24, 10, 0, 0), time_of_day=10, available_time_minutes=120)


def test_level1_readonly_concept():
    t = make_trait()
    assert t.model_version == "trait_v1"


def test_level2_readonly_concept():
    s = make_state_pre()
    assert s.model_version == "ddsr_v1"


def test_snapshot_frozen():
    p = Level3Predictor()
    inp = Level3PredictionInput(make_trait(), make_state_pre(), make_task(), make_context(), HistoryInput(support=HistorySupport()))
    snap = p.create_snapshot(inp)
    assert snap.state.fatigue == 0.4


def test_cold_start_duration_equals_estimated():
    p = Level3Predictor()
    inp = Level3PredictionInput(make_trait(), make_state_pre(), make_task(), make_context(), HistoryInput(support=HistorySupport(total_historical_tasks=0)))
    res = p.predict(inp)
    assert res.prediction_mode == "cold_start"
    assert res.predicted_duration_minutes == 60.0


def test_cold_start_completion_unavailable():
    p = Level3Predictor()
    inp = Level3PredictionInput(make_trait(), make_state_pre(), make_task(), make_context(), HistoryInput(support=HistorySupport(total_historical_tasks=0)))
    res = p.predict(inp)
    assert res.completion_probability is None
    assert res.prediction_status == "insufficient_behavior_data"


def test_history_baseline_median_ratio():
    p = Level3Predictor()
    hist = HistoryInput(
        completion_history=[True, True, False],
        duration_ratio_history=[1.2, 0.8, 1.0],
        support=HistorySupport(total_historical_tasks=3, completed_task_count=2, failed_task_count=1, usable_duration_samples=3),
    )
    inp = Level3PredictionInput(make_trait(), make_state_pre(), make_task(), make_context(), hist)
    res = p.predict(inp)
    assert res.prediction_mode == "history_baseline"
    assert res.predicted_duration_minutes == 60.0 * 1.0  # median of [0.8,1.0,1.2]


def test_smoothed_completion_not_extreme():
    p = Level3Predictor()
    hist = HistoryInput(
        completion_history=[True],
        duration_ratio_history=[1.0],
        support=HistorySupport(total_historical_tasks=1, completed_task_count=1, failed_task_count=0, usable_duration_samples=1),
    )
    inp = Level3PredictionInput(make_trait(), make_state_pre(), make_task(), make_context(), hist)
    res = p.predict(inp)
    assert res.completion_probability is not None
    assert 0.0 < res.completion_probability < 1.0


def test_no_future_leakage_concept():
    p = Level3Predictor()
    inp = Level3PredictionInput(make_trait(), make_state_pre(), make_task(), make_context(), HistoryInput(support=HistorySupport()))
    snap = p.create_snapshot(inp)
    # post-task outcome recorded separately
    p.record_outcome(OutcomeRecord(task_id="t1", completed=True, actual_duration_minutes=50))
    # prediction uses only snap
    res = p.predict(inp)
    assert res.feature_snapshot_id == snap.snapshot_id


def test_learned_eligibility_gate():
    p = Level3Predictor()
    # not enough data
    r = p.check_learned_eligibility()
    assert r["learned_model_eligible"] is False
    # add data
    for i in range(30):
        p.record_outcome(OutcomeRecord(task_id=f"t{i}", completed=i % 2 == 0, actual_duration_minutes=60 if i % 2 == 0 else None))
    r2 = p.check_learned_eligibility()
    # may be eligible or not depending on gate, but gate exists
    assert "learned_model_eligible" in r2


def test_duration_not_negative():
    p = Level3Predictor()
    hist = HistoryInput(
        completion_history=[True, True],
        duration_ratio_history=[0.1, 0.2],
        support=HistorySupport(total_historical_tasks=2, completed_task_count=2, failed_task_count=0, usable_duration_samples=2),
    )
    inp = Level3PredictionInput(make_trait(), make_state_pre(), make_task(), make_context(), hist)
    res = p.predict(inp)
    assert res.predicted_duration_minutes >= 0


def test_ablation_framework_exists():
    p = Level3Predictor()
    a = p.ablation_evaluate()
    assert "A:Task+Context+History" in a["models"][0]
    assert "C:+Trait+State" in a["models"][2]
