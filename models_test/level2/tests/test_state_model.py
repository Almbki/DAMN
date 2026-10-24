from __future__ import annotations

import pytest
from ddsr.config import ALLOWED_SOURCE_CATEGORIES, DDSRConfig
from ddsr.schemas import (
    Direction,
    EvidenceAvailability,
    EvidenceItem,
    EvidenceType,
    Period,
    ReflectionField,
    StateName,
    Strength,
)
from ddsr.state_model import (
    cold_start,
    correct,
    predict_next,
    prediction_error,
)
from ddsr.task_metrics import derive_behavioral_indicators
from helpers import day, execution, plan


def evidence(
    evidence_type: EvidenceType = EvidenceType.FATIGUE,
    direction: Direction = Direction.INCREASE,
    strength: Strength = Strength.STRONG,
    text: str = "explicit evidence",
) -> EvidenceItem:
    return EvidenceItem(
        evidence_type=evidence_type,
        direction=direction,
        strength=strength,
        period=Period.UNSPECIFIED,
        evidence_text=text,
        source_field=ReflectionField.STATE_REVIEW,
    )


def empty_indicators(config: DDSRConfig):
    return derive_behavioral_indicators(
        day(), config, evidence=[], reflection_present=False
    )


def test_cold_start_is_transparent(config):
    prior = cold_start(config)
    assert prior.source == "cold_start_population_prior"
    assert prior.gap_days == 0
    for state in ("fatigue", "stress", "self_efficacy"):
        assert prior.value[state] == 0.5
        assert prior.uncertainty[state] == 0.25


def test_predict_next_one_step_math(config):
    prior = predict_next(
        {"fatigue": 0.8, "stress": 0.8, "self_efficacy": 0.8},
        {"fatigue": 0.1, "stress": 0.1, "self_efficacy": 0.1},
        config,
    )
    # 0.6*0.8 + 0.4*0.5 = 0.68
    assert prior.value["fatigue"] == pytest.approx(0.68)
    expected_sd = (0.6 * 0.1) ** 2 + 0.12**2
    assert prior.uncertainty["fatigue"] == pytest.approx(expected_sd**0.5)


def test_predict_next_is_bounded_and_does_not_lock(config):
    prior = predict_next(
        {"fatigue": 0.95, "stress": 0.02, "self_efficacy": 0.95},
        {"fatigue": 0.02, "stress": 0.02, "self_efficacy": 0.02},
        config,
        steps=100,
    )
    for state in ("fatigue", "stress", "self_efficacy"):
        assert 0.0 <= prior.value[state] <= 1.0
        assert config.uncertainty_floor <= prior.uncertainty[state] <= config.uncertainty_ceiling
    assert prior.value["fatigue"] == pytest.approx(0.5, abs=1e-6)
    assert prior.value["stress"] == pytest.approx(0.5, abs=1e-6)


def test_correction_moves_fatigue_in_the_evidence_direction(config):
    prior = cold_start(config)
    indicators = empty_indicators(config)
    baseline = correct(prior, [], indicators, config)
    increased = correct(
        prior, [evidence(EvidenceType.FATIGUE, Direction.INCREASE)], indicators, config
    )
    decreased = correct(
        prior, [evidence(EvidenceType.FATIGUE, Direction.DECREASE)], indicators, config
    )
    assert increased.posterior["fatigue"] > baseline.posterior["fatigue"]
    assert decreased.posterior["fatigue"] < baseline.posterior["fatigue"]
    assert increased.uncertainty["fatigue"] < baseline.uncertainty["fatigue"]
    assert decreased.uncertainty["fatigue"] < baseline.uncertainty["fatigue"]


def test_missing_evidence_leaves_posterior_at_prior(config):
    prior = cold_start(config)
    result = correct(prior, [], empty_indicators(config), config)
    for state in ("fatigue", "stress", "self_efficacy"):
        assert result.posterior[state] == pytest.approx(prior.value[state])
        assert result.uncertainty[state] <= prior.uncertainty[state]
        assert result.evidence_counts[state] == 0
        assert result.evidence_availability[state] is EvidenceAvailability.NONE


def test_conflicting_evidence_keeps_mean_near_prior_and_flags_conflict(config):
    prior = cold_start(config)
    indicators = empty_indicators(config)
    baseline = correct(prior, [], indicators, config)
    result = correct(
        prior,
        [
            evidence(EvidenceType.FATIGUE, Direction.INCREASE),
            evidence(EvidenceType.FATIGUE, Direction.DECREASE),
        ],
        indicators,
        config,
    )
    assert result.posterior["fatigue"] == pytest.approx(0.5, abs=1e-6)
    # Two exactly symmetric likelihoods cancel, so the posterior equals the
    # prior; the conflict is still flagged and neither side is silently dropped.
    assert result.uncertainty["fatigue"] == pytest.approx(
        baseline.uncertainty["fatigue"]
    )
    assert StateName.FATIGUE in result.conflict_states
    assert result.evidence_counts["fatigue"] == 2


def test_goal_attainment_updates_only_self_efficacy(config):
    prior = cold_start(config)
    indicators = derive_behavioral_indicators(
        day(
            plans=[plan("t1")],
            executions=[execution("t1", completion=1.0, completed=True)],
        ),
        config,
        evidence=[],
        reflection_present=False,
    )
    result = correct(prior, [], indicators, config)
    assert result.posterior["self_efficacy"] > prior.value["self_efficacy"]
    assert result.posterior["fatigue"] == pytest.approx(prior.value["fatigue"])
    assert result.posterior["stress"] == pytest.approx(prior.value["stress"])
    assert (
        result.evidence_availability["self_efficacy"]
        is EvidenceAvailability.TASK_LOG_ONLY
    )


def test_low_goal_attainment_lowers_self_efficacy(config):
    prior = cold_start(config)
    indicators = derive_behavioral_indicators(
        day(
            plans=[plan("t1")],
            executions=[execution("t1", completion=0.0, completed=False)],
        ),
        config,
        evidence=[],
        reflection_present=False,
    )
    result = correct(prior, [], indicators, config)
    assert result.posterior["self_efficacy"] < prior.value["self_efficacy"]


def test_procrastination_evidence_never_changes_states(config):
    prior = cold_start(config)
    indicators = empty_indicators(config)
    item = EvidenceItem(
        evidence_type=EvidenceType.PROCRASTINATION,
        direction=Direction.INCREASE,
        strength=Strength.STRONG,
        period=Period.EVENING,
        cause_category=None,
        voluntary=True,
        evidence_text="我一直在拖延",
        source_field=ReflectionField.STUCK_POINTS,
    )
    result = correct(prior, [item], indicators, config)
    for state in ("fatigue", "stress", "self_efficacy"):
        assert result.posterior[state] == pytest.approx(prior.value[state])


def test_interruption_evidence_never_changes_states(config):
    prior = cold_start(config)
    indicators = empty_indicators(config)
    item = EvidenceItem(
        evidence_type=EvidenceType.INTERRUPTION,
        direction=Direction.INCREASE,
        strength=Strength.STRONG,
        period=Period.AFTERNOON,
        cause_category="external_interruption",
        voluntary=False,
        evidence_text="临时开会",
        source_field=ReflectionField.STUCK_POINTS,
    )
    result = correct(prior, [item], indicators, config)
    for state in ("fatigue", "stress", "self_efficacy"):
        assert result.posterior[state] == pytest.approx(prior.value[state])


def test_evidence_availability_reflection_and_task_log(config):
    prior = cold_start(config)
    indicators = derive_behavioral_indicators(
        day(
            plans=[plan("t1")],
            executions=[execution("t1", completion=1.0, completed=True)],
        ),
        config,
        evidence=[],
        reflection_present=True,
    )
    result = correct(
        prior,
        [evidence(EvidenceType.SELF_EFFICACY, Direction.INCREASE)],
        indicators,
        config,
    )
    assert (
        result.evidence_availability["self_efficacy"]
        is EvidenceAvailability.REFLECTION_AND_TASK_LOG
    )
    assert result.evidence_availability["fatigue"] is EvidenceAvailability.NONE


def test_prediction_error_is_posterior_minus_prior(config):
    prior = cold_start(config)
    indicators = empty_indicators(config)
    result = correct(
        prior, [evidence(EvidenceType.STRESS, Direction.INCREASE)], indicators, config
    )
    raw, standardized = prediction_error(result.posterior, prior)
    for state in ("fatigue", "stress", "self_efficacy"):
        assert raw[state] == pytest.approx(result.posterior[state] - prior.value[state])
        assert standardized[state] == pytest.approx(
            raw[state] / prior.uncertainty[state]
        )


def test_extreme_evidence_stays_bounded(config):
    prior = cold_start(config)
    indicators = empty_indicators(config)
    items = [
        evidence(EvidenceType.FATIGUE, Direction.INCREASE) for _ in range(20)
    ]
    result = correct(prior, items, indicators, config)
    assert 0.0 <= result.posterior["fatigue"] <= 1.0
    assert result.posterior["fatigue"] > 0.95
    assert result.uncertainty["fatigue"] >= config.uncertainty_floor
    assert result.uncertainty["fatigue"] <= config.uncertainty_ceiling


def test_parameter_provenance_is_complete_and_labeled(config):
    assert config.parameter_sources
    for name, entry in config.parameter_sources.items():
        assert entry["category"] in ALLOWED_SOURCE_CATEGORIES, name
        assert entry["note"].strip(), name
    assert config.personalization_enabled is False
    # The JSON config must round-trip to the same values.
    loaded = DDSRConfig.from_json()
    assert loaded.config_version == config.config_version
    assert loaded.parameter_sources == config.parameter_sources
