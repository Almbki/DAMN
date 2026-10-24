from __future__ import annotations

from datetime import date

import pytest
from ddsr.engine import DDSREngine
from ddsr.schemas import DayInput, ReflectionInput
from ddsr.task_metrics import derive_behavioral_indicators, derive_task_metrics
from ddsr.trait_context import TraitContext
from helpers import day, deep_copy, execution, plan, trait_profile
from pydantic import ValidationError


def test_trait_profile_is_read_only_and_versioned(trait_dict):
    original = deep_copy(trait_dict)
    context = TraitContext.from_profile(trait_dict)
    assert trait_dict == original
    assert context.model == "trait_v1"
    assert context.schema_version == "1.0"
    assert context.calibration_model == "samejima_grm"
    assert context.calibration_version == "grm_v1"
    assert context.reference_population == "Johnson_IPIP_NEO_120"
    assert set(context.domains) == set("NEOAC")
    # The copy is independent from the caller's profile.
    context.domains["N"]["theta"] = 99.0
    assert trait_dict["domains"]["N"]["theta"] == 0.0


def test_trait_profile_rejects_missing_domain(trait_dict):
    del trait_dict["domains"]["C"]
    with pytest.raises(ValueError, match="missing domains"):
        TraitContext.from_profile(trait_dict)


def test_trait_profile_rejects_bad_se(trait_dict):
    trait_dict["domains"]["N"]["se"] = 0
    with pytest.raises(ValueError, match="se must be > 0"):
        TraitContext.from_profile(trait_dict)


def test_trait_theta_does_not_change_daily_states(config):
    low = TraitContext.from_profile(trait_profile(theta=-1.5))
    high = TraitContext.from_profile(trait_profile(theta=1.5))
    example = day(
        reflection=ReflectionInput(state_review="今天很累，压力很大。"),
    )
    low_profile = DDSREngine(config).process_day(example, low)
    high_profile = DDSREngine(config).process_day(example, high)
    assert low_profile.current_posterior.model_dump() == high_profile.current_posterior.model_dump()
    assert low_profile.fatigue.model_dump() == high_profile.fatigue.model_dump()
    assert low_profile.stress.model_dump() == high_profile.stress.model_dump()
    assert low_profile.self_efficacy.model_dump() == high_profile.self_efficacy.model_dump()


def test_task_metrics_start_delay_ratio_and_attainment(config):
    example = day(
        plans=[plan("t1", hour=9)],
        executions=[
            execution(
                "t1",
                start_hour=9,
                start_minute=30,
                duration=90,
                completion=0.8,
                completed=True,
                interruptions=1,
            )
        ],
    )
    [derived] = derive_task_metrics(example, config)
    assert derived.started is True
    assert derived.start_delay_minutes == pytest.approx(30.0)
    assert derived.duration_ratio == pytest.approx(1.5)
    assert derived.completion_ratio == pytest.approx(0.8)
    assert derived.late_start_candidate is False  # 30 < 60
    assert derived.evidence_available is True

    indicators = derive_behavioral_indicators(example, config, [], True)
    assert indicators.initiation.tasks_with_log == 1
    assert indicators.initiation.start_rate == pytest.approx(1.0)
    assert indicators.initiation.on_time_tasks == 0
    assert indicators.persistence.mean_duration_ratio == pytest.approx(1.5)
    assert indicators.persistence.continuation_rate == pytest.approx(1.0)
    assert indicators.goal_attainment.value == pytest.approx(0.8)


def test_missing_execution_is_unavailable_not_zero(config):
    example = day(plans=[plan("t1", hour=9)])
    [derived] = derive_task_metrics(example, config)
    assert derived.started is False
    assert derived.completion_ratio is None
    indicators = derive_behavioral_indicators(example, config, [], False)
    assert indicators.initiation.tasks_with_log == 0
    assert indicators.initiation.start_rate is None
    assert indicators.initiation.evidence_available is False
    assert indicators.goal_attainment.value is None
    assert indicators.goal_attainment.evidence_available is False
    assert indicators.persistence.continuation_rate is None
    assert indicators.procrastination_evidence.candidate_task_ids == []


def test_completed_true_defaults_completion_to_one(config):
    example = day(
        plans=[plan("t1", hour=9)],
        executions=[execution("t1", completion=None, completed=True)],
    )
    [derived] = derive_task_metrics(example, config)
    assert derived.completion_ratio == 1.0
    indicators = derive_behavioral_indicators(example, config, [], False)
    assert indicators.goal_attainment.value == 1.0


def test_duplicate_task_ids_rejected():
    with pytest.raises(ValidationError, match="unique task_id"):
        DayInput(
            date=date(2026, 10, 20),
            task_plans=[plan("t1"), plan("t1")],
        )


def test_execution_for_unknown_task_rejected():
    with pytest.raises(ValidationError, match="unknown task ids"):
        DayInput(
            date=date(2026, 10, 20),
            task_plans=[plan("t1")],
            task_executions=[execution("t2")],
        )


def test_late_start_is_only_a_candidate(config):
    example = day(
        plans=[plan("t1", hour=9)],
        executions=[
            execution("t1", start_hour=11, duration=30, completion=0.5, completed=False)
        ],
    )
    indicators = derive_behavioral_indicators(example, config, [], True)
    assert indicators.procrastination_evidence.confirmed == []
    assert indicators.procrastination_evidence.candidate_task_ids == ["t1"]
    assert indicators.procrastination_evidence.late_start_candidate_count == 1
    assert "not procrastination" in indicators.procrastination_evidence.note
