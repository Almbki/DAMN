"""Unit tests for the pure feedback replan policy."""

from __future__ import annotations

from app.domain.feedback.policy import decide_feedback_replan


def test_completion_rate_alone_never_replans() -> None:
    decision = decide_feedback_replan(
        stress=None,
        energy=None,
        completion_rate=0.05,
        duration_bias=0.0,
        portrait_decision="none",
    )
    assert decision.route == "none"
    assert decision.pressure == "none"
    assert decision.signals["pressure_high"] is False


def test_completion_only_does_not_even_wake_the_portrait() -> None:
    decision = decide_feedback_replan(
        stress=None,
        energy=None,
        completion_rate=0.05,
        duration_bias=0.0,
        portrait_decision="full_replan",
    )
    assert decision.route == "none"


def test_high_stress_pressure_is_enough_for_a_micro_adjustment() -> None:
    decision = decide_feedback_replan(
        stress=7.0,
        energy=6.0,
        completion_rate=0.9,
        duration_bias=0.0,
        portrait_decision="none",
    )
    assert decision.route == "micro_adjust"
    assert decision.pressure == "high"


def test_low_energy_is_enough_for_a_micro_adjustment() -> None:
    decision = decide_feedback_replan(
        stress=3.0,
        energy=4.0,
        completion_rate=0.9,
        duration_bias=0.0,
        portrait_decision="none",
    )
    assert decision.route == "micro_adjust"
    assert decision.pressure == "high"


def test_severe_pressure_plus_low_completion_is_a_full_replan() -> None:
    decision = decide_feedback_replan(
        stress=9.0,
        energy=2.0,
        completion_rate=0.4,
        duration_bias=0.0,
        portrait_decision="none",
    )
    assert decision.route == "full_replan"
    assert decision.pressure == "severe"


def test_severe_pressure_with_high_completion_stays_a_micro_adjustment() -> None:
    decision = decide_feedback_replan(
        stress=9.0,
        energy=2.0,
        completion_rate=0.95,
        duration_bias=0.0,
        portrait_decision="none",
    )
    assert decision.route == "micro_adjust"
    assert decision.pressure == "severe"


def test_high_duration_bias_alone_is_a_micro_adjustment() -> None:
    decision = decide_feedback_replan(
        stress=3.0,
        energy=8.0,
        completion_rate=0.9,
        duration_bias=0.8,
        portrait_decision="none",
    )
    assert decision.route == "micro_adjust"
    assert decision.pressure == "none"


def test_portrait_full_replan_counts_under_pressure() -> None:
    decision = decide_feedback_replan(
        stress=8.0,
        energy=6.0,
        completion_rate=0.9,
        duration_bias=0.0,
        portrait_decision="full_replan",
    )
    assert decision.route == "full_replan"


def test_portrait_local_repair_is_gated_by_pressure_or_duration_bias() -> None:
    gated = decide_feedback_replan(
        stress=3.0,
        energy=8.0,
        completion_rate=0.9,
        duration_bias=0.0,
        portrait_decision="local_repair",
    )
    assert gated.route == "none"

    active = decide_feedback_replan(
        stress=7.0,
        energy=8.0,
        completion_rate=0.9,
        duration_bias=0.0,
        portrait_decision="local_repair",
    )
    assert active.route == "micro_adjust"


def test_thresholds_are_configurable() -> None:
    decision = decide_feedback_replan(
        stress=6.0,
        energy=8.0,
        completion_rate=0.9,
        duration_bias=0.0,
        portrait_decision="none",
        stress_high=5.0,
    )
    assert decision.route == "micro_adjust"


def test_decision_keeps_the_signals_it_used() -> None:
    decision = decide_feedback_replan(
        stress=9.0,
        energy=2.0,
        completion_rate=0.3,
        duration_bias=0.7,
        portrait_decision="none",
    )
    assert decision.signals["stress"] == 9.0
    assert decision.signals["energy"] == 2.0
    assert decision.signals["completion_rate"] == 0.3
    assert decision.signals["duration_bias"] == 0.7
    assert decision.reason
