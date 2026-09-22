"""Unit tests for the user-portrait engine (pure domain, no I/O)."""

from __future__ import annotations

import pytest

from app.domain.profile import (
    MBTI_TEMPLATES,
    UserProfileData,
    UserStateData,
    init_state,
    predict_completion,
    predict_duration,
    profile_prompt_json,
    replan_decision,
    resolve_mbti_type,
    should_prompt,
    update_state,
)


# ---------------------------------------------------------------------------
# type resolution
# ---------------------------------------------------------------------------
def test_explicit_type_is_used() -> None:
    assert resolve_mbti_type(UserProfileData(mbti_type="intp")) == "INTP"


def test_invalid_type_falls_back_to_default() -> None:
    assert resolve_mbti_type(UserProfileData(mbti_type="ZZZZ")) == "_default"
    assert resolve_mbti_type(UserProfileData()) == "_default"


def test_dimension_weights_override_letters() -> None:
    profile = UserProfileData(mbti_type="INTJ", mbti_dims={"ie": 0.2, "jp": 0.9})
    # ie=0.2 -> minority E; jp=0.9 -> majority J
    assert resolve_mbti_type(profile) == "ENTJ"


def test_dimensions_without_a_type_resolve_or_default() -> None:
    # Only one dimension is known, so the rest stay unknown -> not a valid type.
    assert resolve_mbti_type(UserProfileData(mbti_dims={"ie": 0.9})) == "_default"


# ---------------------------------------------------------------------------
# state initialisation
# ---------------------------------------------------------------------------
def test_init_state_is_an_exact_template_copy_without_dims() -> None:
    state = init_state(UserProfileData(mbti_type="INTP"))
    template = MBTI_TEMPLATES["INTP"]
    assert state.duration_factor == template["duration_factor"]
    assert state.completion_prob == template["completion_prob"]
    assert state.preferred_time_slots == template["preferred_time_slots"]
    # Dynamic fields start neutral and nothing has been observed yet.
    assert state.state_energy == 0.5
    assert state.state_fatigue == 0.5
    assert state.self_efficacy == 0.5
    assert state.update_count == 0
    assert state.is_degraded() is True


def test_init_state_blends_two_templates_on_dimension_weights() -> None:
    # ie=0.25 -> 25% I / 75% E, so E is the MAJORITY letter and the resolved
    # type is ENTJ. The numeric fields blend 0.25*I + 0.75*E; the non-numeric
    # preferred_time_slots come from the majority type (ENTJ).
    state = init_state(UserProfileData(mbti_type="INTJ", mbti_dims={"ie": 0.25}))
    intj = MBTI_TEMPLATES["INTJ"]
    entj = MBTI_TEMPLATES["ENTJ"]
    expected = 0.25 * intj["duration_factor"] + 0.75 * entj["duration_factor"]
    assert state.duration_factor == pytest.approx(expected)
    assert resolve_mbti_type(UserProfileData(mbti_type="INTJ", mbti_dims={"ie": 0.25})) == "ENTJ"
    assert state.preferred_time_slots == entj["preferred_time_slots"]


def test_minority_weight_is_not_inverted() -> None:
    """``ie=0.2`` means 20% I / 80% E, so the E template must dominate."""
    state = init_state(UserProfileData(mbti_type="INTJ", mbti_dims={"ie": 0.2}))
    intj = MBTI_TEMPLATES["INTJ"]
    entj = MBTI_TEMPLATES["ENTJ"]
    expected = 0.2 * intj["duration_factor"] + 0.8 * entj["duration_factor"]
    assert state.duration_factor == pytest.approx(expected)
    # Regression guard: the old implementation anchored on the majority type and
    # produced 0.2*ENTJ + 0.8*INTJ here.
    assert state.duration_factor != pytest.approx(
        0.2 * entj["duration_factor"] + 0.8 * intj["duration_factor"]
    )


def test_default_profile_still_produces_a_usable_state() -> None:
    state = init_state(UserProfileData())
    assert state.update_count == 0
    assert 0.0 < state.duration_factor < 3.0
    assert 0.0 <= state.completion_prob <= 1.0


# ---------------------------------------------------------------------------
# predictors
# ---------------------------------------------------------------------------
def test_predict_duration_applies_multiplier_and_fatigue() -> None:
    fresh = UserStateData(duration_factor=1.0, state_fatigue=0.5, state_energy=0.5)
    baseline = predict_duration(100, "practice", fresh)
    assert baseline.q50 == pytest.approx(130.0)  # 100 * 1.3 (practice multiplier)
    assert baseline.q80 == pytest.approx(baseline.q50 * 1.25)
    assert baseline.degraded is True  # update_count 0

    tired = UserStateData(
        duration_factor=1.0, state_fatigue=1.0, state_energy=0.5, update_count=5
    )
    assert predict_duration(100, "practice", tired).q50 > baseline.q50
    assert predict_duration(100, "practice", tired).degraded is False


def test_predict_duration_unknown_task_type_uses_neutral_multiplier() -> None:
    state = UserStateData(duration_factor=1.0)
    assert predict_duration(100, "not-a-type", state).q50 == pytest.approx(100.0)


def test_predict_completion_cold_start_uses_the_prior() -> None:
    state = UserStateData(completion_prob=0.8, update_count=0)
    assert predict_completion(state, recent_completion_rate_7d=0.1).prob == pytest.approx(0.8)


def test_predict_completion_blends_once_observed() -> None:
    state = UserStateData(completion_prob=0.8, update_count=4)
    estimate = predict_completion(state, recent_completion_rate_7d=0.4)
    assert estimate.prob == pytest.approx(0.6)  # 0.5*0.8 + 0.5*0.4
    assert estimate.degraded is False


def test_predict_completion_is_clamped() -> None:
    low = predict_completion(UserStateData(completion_prob=0.0, update_count=5), 0.0)
    high = predict_completion(UserStateData(completion_prob=1.0, update_count=5), 1.0)
    assert low.prob == pytest.approx(0.05)
    assert high.prob == pytest.approx(0.98)


# ---------------------------------------------------------------------------
# state updates (EWMA)
# ---------------------------------------------------------------------------
def test_update_state_is_immutable_and_bumps_update_count() -> None:
    original = UserStateData()
    updated = update_state(original, completed=True)
    assert original.update_count == 0  # frozen dataclass untouched
    assert updated.update_count == 1


def test_update_state_moves_duration_factor_toward_the_observed_ratio() -> None:
    state = UserStateData(duration_factor=1.0)
    slower = update_state(state, actual_min=180, theoretical_min=100)
    assert slower.duration_factor == pytest.approx(0.3 * 1.8 + 0.7 * 1.0)
    faster = update_state(state, actual_min=50, theoretical_min=100)
    assert faster.duration_factor == pytest.approx(0.3 * 0.5 + 0.7 * 1.0)


def test_update_state_ignores_a_missing_or_invalid_theoretical_duration() -> None:
    state = UserStateData(duration_factor=1.2)
    assert update_state(state, actual_min=90).duration_factor == pytest.approx(1.2)
    zero_theoretical = update_state(state, actual_min=90, theoretical_min=0)
    assert zero_theoretical.duration_factor == pytest.approx(1.2)


def test_update_state_maps_energy_onto_energy_and_fatigue() -> None:
    updated = update_state(UserStateData(), energy_after=4)
    assert updated.state_energy == pytest.approx(0.3 * 0.4 + 0.7 * 0.5)
    assert updated.state_fatigue == pytest.approx(0.3 * 0.6 + 0.7 * 0.5)


def test_update_state_maps_stress() -> None:
    updated = update_state(UserStateData(), stress_after=8)
    assert updated.stress_baseline == pytest.approx(0.3 * 0.8 + 0.7 * 0.5)


def test_self_efficacy_rises_on_success_and_falls_on_failure() -> None:
    success = update_state(UserStateData(), completed=True)
    failure = update_state(UserStateData(), completed=False, partial_pct=0.0)
    assert success.self_efficacy > 0.5
    assert failure.self_efficacy < 0.5


def test_self_efficacy_uses_partial_completion() -> None:
    half = update_state(UserStateData(), completed=False, partial_pct=0.5)
    # 0.5 + 0.15*0.5*0.5 - 0.25*0.5*0.5 = 0.475 (loss outweighs gain at 50%)
    assert half.self_efficacy == pytest.approx(0.475)


# ---------------------------------------------------------------------------
# replan decision / prompting
# ---------------------------------------------------------------------------
def test_five_low_days_trigger_a_full_replan() -> None:
    decision = replan_decision([0.2, 0.3, 0.1, 0.35, 0.2], 0.0)
    assert decision.decision == "full_replan"
    assert decision.reason_code == "low_completion_5d"


def test_fewer_rates_are_left_padded_with_the_oldest() -> None:
    # [0.3, 0.2] -> padded to [0.3, 0.3, 0.3, 0.3, 0.2]; all < 0.40
    assert replan_decision([0.3, 0.2], 0.0).decision == "full_replan"


def test_two_low_days_trigger_a_local_repair() -> None:
    decision = replan_decision([0.9, 0.9, 0.9, 0.5, 0.55], 0.0)
    assert decision.decision == "local_repair"
    assert decision.reason_code == "low_completion_2d"


def test_duration_bias_alone_triggers_a_local_repair() -> None:
    decision = replan_decision([0.9, 0.9, 0.9], 0.8)
    assert decision.decision == "local_repair"
    assert decision.reason_code == "duration_bias_high"


def test_healthy_plan_needs_no_action() -> None:
    assert replan_decision([0.9, 0.95, 0.8], 0.1).decision == "none"
    assert replan_decision([], 0.0).decision == "none"


def test_should_prompt_respects_budget_focus_and_fatigue() -> None:
    assert should_prompt(0, False, 0.2) == "send"
    assert should_prompt(3, False, 0.2) == "defer"
    assert should_prompt(0, True, 0.2) == "defer"
    assert should_prompt(0, False, 0.9) == "defer"


# ---------------------------------------------------------------------------
# prompt payload
# ---------------------------------------------------------------------------
def test_profile_prompt_json_is_json_safe_and_complete() -> None:
    profile = UserProfileData(mbti_type="INTP", identity="研究生")
    payload = profile_prompt_json(profile, init_state(profile))
    import json

    json.dumps(payload)  # must be serialisable
    assert payload["mbti_type"] == "INTP"
    assert payload["identity"] == "研究生"
    assert payload["update_count"] == 0
    for key in ("duration_factor", "completion_prob", "self_efficacy", "preferred_time_slots"):
        assert key in payload


def test_profile_prompt_json_omits_absent_identity() -> None:
    profile = UserProfileData(mbti_type="INTJ")
    payload = profile_prompt_json(profile, init_state(profile))
    assert "identity" not in payload
