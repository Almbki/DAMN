"""Unit tests for the pure MBTI user-profile domain module.

Covers ``app/domain/profile``: template table shape, type resolution,
percentage-weight blending, the three predictors, EWMA state updates, the two
decision helpers and the 环节-2 prompt JSON. Pure stdlib - no DB, no app wiring.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.domain.profile import (
    DIMENSION_LETTERS,
    MBTI_DIMENSIONS,
    MBTI_TEMPLATES,
    TYPE_MULTIPLIER,
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

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

_NUMERIC_TEMPLATE_KEYS = (
    "duration_factor",
    "completion_prob",
    "stress_baseline",
    "energy_drain_rate",
    "proactive_score",
    "procrastination_tendency",
    "stress_response",
)
_SLOT_KEYS = {"high", "medium", "low", "restorative"}
_SLOT_VALUES = {"morning", "afternoon", "evening", "night"}

_PROMPT_KEYS = {
    "mbti_type",
    "identity",
    "duration_factor",
    "completion_prob",
    "self_efficacy",
    "state_energy",
    "state_fatigue",
    "stress_baseline",
    "procrastination_tendency",
    "proactive_score",
    "preferred_time_slots",
    "update_count",
}


def _state(**overrides: object) -> UserStateData:
    """A neutral, template-free state for arithmetic checks."""
    base = {
        "duration_factor": 1.0,
        "completion_prob": 0.7,
        "stress_baseline": 0.5,
        "state_energy": 0.5,
        "state_fatigue": 0.5,
        "self_efficacy": 0.5,
        "update_count": 0,
    }
    base.update(overrides)
    return UserStateData(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# mbti_templates
# --------------------------------------------------------------------------- #


def test_dimension_constants() -> None:
    assert MBTI_DIMENSIONS == ("ie", "sn", "tf", "jp")
    assert DIMENSION_LETTERS == {
        "ie": ("I", "E"),
        "sn": ("S", "N"),
        "tf": ("T", "F"),
        "jp": ("J", "P"),
    }


def test_templates_include_16_types_and_default() -> None:
    assert len(MBTI_TEMPLATES) == 17
    assert "_default" in MBTI_TEMPLATES
    assert {"INTP", "ENTP", "INTJ", "ESFJ"} <= set(MBTI_TEMPLATES)


def test_every_template_has_exactly_eight_keys() -> None:
    for name, tmpl in MBTI_TEMPLATES.items():
        assert set(tmpl) == set(_NUMERIC_TEMPLATE_KEYS) | {"preferred_time_slots"}, name
        slots = tmpl["preferred_time_slots"]
        assert isinstance(slots, dict)
        assert set(slots) == _SLOT_KEYS, name
        assert set(slots.values()) <= _SLOT_VALUES, name
        assert 0.8 <= float(tmpl["duration_factor"]) <= 1.6, name
        for key in _NUMERIC_TEMPLATE_KEYS[1:]:
            assert 0.0 <= float(tmpl[key]) <= 1.0, (name, key)


def test_default_template_is_neutral() -> None:
    tmpl = MBTI_TEMPLATES["_default"]
    assert tmpl["duration_factor"] == 1.3
    assert tmpl["completion_prob"] == 0.7
    for key in _NUMERIC_TEMPLATE_KEYS[2:]:
        assert tmpl[key] == 0.5


def test_type_multiplier_contract() -> None:
    assert TYPE_MULTIPLIER == {
        "concept": 1.2,
        "example": 1.1,
        "practice": 1.3,
        "review": 0.6,
        "project": 1.8,
    }


# --------------------------------------------------------------------------- #
# init_state / resolution
# --------------------------------------------------------------------------- #


def test_init_hard_classification_intp() -> None:
    state = init_state(UserProfileData(mbti_type="INTP"))
    intp = MBTI_TEMPLATES["INTP"]
    assert state.duration_factor == intp["duration_factor"]
    assert state.completion_prob == intp["completion_prob"]
    assert state.procrastination_tendency == intp["procrastination_tendency"]
    assert state.preferred_time_slots == intp["preferred_time_slots"]
    assert state.state_energy == 0.5
    assert state.state_fatigue == 0.5
    assert state.self_efficacy == 0.5
    assert state.update_count == 0


def test_init_is_case_insensitive() -> None:
    assert resolve_mbti_type(UserProfileData(mbti_type="intp")) == "INTP"
    assert (
        init_state(UserProfileData(mbti_type="  entp ")).duration_factor
        == MBTI_TEMPLATES["ENTP"]["duration_factor"]
    )


def test_init_unknown_or_missing_type_falls_back_to_default() -> None:
    for profile in (
        UserProfileData(mbti_type="ZZZZ"),
        UserProfileData(mbti_type=None),
        UserProfileData(mbti_type=""),
    ):
        assert resolve_mbti_type(profile) == "_default"
        state = init_state(profile)
        assert state.duration_factor == MBTI_TEMPLATES["_default"]["duration_factor"]
        assert state.completion_prob == MBTI_TEMPLATES["_default"]["completion_prob"]


def test_init_dims_only_resolves_majority_type() -> None:
    profile = UserProfileData(
        mbti_type=None, mbti_dims={"ie": 0.9, "sn": 0.1, "tf": 0.9, "jp": 0.1}
    )
    assert resolve_mbti_type(profile) == "INTP"
    # Dims are present, so numeric fields are blended around the INTP template
    # while slots always follow the resolved type.
    state = init_state(profile)
    assert state.preferred_time_slots == MBTI_TEMPLATES["INTP"]["preferred_time_slots"]


def test_init_weighted_dim_blending_math() -> None:
    # ie=0.65 on INTP -> 0.65*INTP + 0.35*ENTP (INTP and ENTP differ only in ie).
    state = init_state(UserProfileData(mbti_type="INTP", mbti_dims={"ie": 0.65}))
    intp = MBTI_TEMPLATES["INTP"]
    entp = MBTI_TEMPLATES["ENTP"]
    assert state.duration_factor == pytest.approx(
        0.65 * intp["duration_factor"] + 0.35 * entp["duration_factor"]
    )
    assert state.proactive_score == pytest.approx(
        0.65 * intp["proactive_score"] + 0.35 * entp["proactive_score"]
    )
    # Slots stay with the resolved (INTP) type.
    assert state.preferred_time_slots == intp["preferred_time_slots"]


def test_init_majority_letter_override_uses_flipped_family() -> None:
    # ie=0.2 -> 20% I / 80% E, so the resolved type is ENTP and slots come from it.
    profile = UserProfileData(mbti_type="INTP", mbti_dims={"ie": 0.2})
    assert resolve_mbti_type(profile) == "ENTP"
    state = init_state(profile)
    assert state.preferred_time_slots == MBTI_TEMPLATES["ENTP"]["preferred_time_slots"]
    assert state.duration_factor == pytest.approx(
        0.2 * MBTI_TEMPLATES["ENTP"]["duration_factor"]
        + 0.8 * MBTI_TEMPLATES["INTP"]["duration_factor"]
    )


# --------------------------------------------------------------------------- #
# predict_duration
# --------------------------------------------------------------------------- #


def test_predict_duration_hand_computed() -> None:
    state = _state(duration_factor=1.0, state_fatigue=0.5, state_energy=0.5)
    est = predict_duration(60.0, "concept", state)
    assert est.q50 == pytest.approx(60.0 * 1.2)
    assert est.q80 == pytest.approx(72.0 * 1.25)
    assert est.degraded is True


def test_predict_duration_full_formula() -> None:
    state = _state(duration_factor=2.0, state_fatigue=0.8, state_energy=0.2)
    est = predict_duration(50.0, "practice", state)
    # base = 50*1.3 = 65; fatigue = 1+0.3*0.3 = 1.09; energy = 1-0.2*(-0.3) = 1.06
    expected_q50 = 65.0 * 2.0 * 1.09 * 1.06
    assert est.q50 == pytest.approx(expected_q50)
    assert est.q80 == pytest.approx(expected_q50 * 1.25)


def test_predict_duration_unknown_task_type_uses_one() -> None:
    state = _state(duration_factor=1.0)
    est = predict_duration(40.0, "does-not-exist", state)
    assert est.q50 == pytest.approx(40.0)


def test_predict_duration_degraded_boundary() -> None:
    assert predict_duration(10.0, "review", _state(update_count=2)).degraded is True
    assert predict_duration(10.0, "review", _state(update_count=3)).degraded is False


# --------------------------------------------------------------------------- #
# predict_completion
# --------------------------------------------------------------------------- #


def test_predict_completion_cold_start_uses_prior() -> None:
    state = _state(completion_prob=0.7, update_count=0)
    est = predict_completion(state, recent_completion_rate_7d=0.2)
    assert est.prob == pytest.approx(0.7)
    assert est.degraded is True

    # updated once but no 7d rate -> still cold.
    est = predict_completion(_state(completion_prob=0.7, update_count=1), None)
    assert est.prob == pytest.approx(0.7)


def test_predict_completion_blends_prior_and_recent_rate() -> None:
    est = predict_completion(
        _state(completion_prob=0.7, update_count=3), recent_completion_rate_7d=0.5
    )
    assert est.prob == pytest.approx(0.5 * 0.7 + 0.5 * 0.5)
    assert est.degraded is False


def test_predict_completion_clamps_to_band() -> None:
    assert predict_completion(_state(completion_prob=1.0)).prob == pytest.approx(0.98)
    assert predict_completion(_state(completion_prob=0.0)).prob == pytest.approx(0.05)


# --------------------------------------------------------------------------- #
# update_state
# --------------------------------------------------------------------------- #


def test_update_state_ewma_numbers() -> None:
    state = _state(duration_factor=1.0, update_count=0)
    new = update_state(
        state,
        actual_min=120.0,
        theoretical_min=60.0,
        completed=True,
        energy_after=8.0,
        stress_after=6.0,
    )
    assert new.duration_factor == pytest.approx(0.3 * 2.0 + 0.7 * 1.0)  # 1.30
    assert new.state_energy == pytest.approx(0.3 * 0.8 + 0.7 * 0.5)  # 0.59
    assert new.state_fatigue == pytest.approx(0.3 * 0.2 + 0.7 * 0.5)  # 0.41
    assert new.stress_baseline == pytest.approx(0.3 * 0.6 + 0.7 * 0.5)  # 0.53
    assert new.self_efficacy == pytest.approx(0.5 + 0.15 * 1.0 * 0.5)  # 0.575
    assert new.update_count == 1


def test_update_state_does_not_mutate_input() -> None:
    state = _state(duration_factor=1.0, update_count=0)
    new = update_state(state, actual_min=120.0, theoretical_min=60.0, completed=True)
    assert new is not state
    assert state.duration_factor == 1.0
    assert state.update_count == 0
    assert state.self_efficacy == 0.5


def test_update_state_without_observations_still_increments_count() -> None:
    state = _state(update_count=4)
    new = update_state(state)
    assert new == dataclasses.replace(state, update_count=5)


def test_update_state_duration_ratio_clamped() -> None:
    new = update_state(_state(duration_factor=1.0), actual_min=1000.0, theoretical_min=1.0)
    assert new.duration_factor == pytest.approx(0.3 * 3.0 + 0.7 * 1.0)
    new = update_state(_state(duration_factor=1.0), actual_min=1.0, theoretical_min=1000.0)
    assert new.duration_factor == pytest.approx(0.3 * 0.5 + 0.7 * 1.0)


def test_update_state_self_efficacy_up_on_success_down_on_failure() -> None:
    up = update_state(_state(self_efficacy=0.5), completed=True)
    assert up.self_efficacy > 0.5
    down = update_state(_state(self_efficacy=0.5), completed=False)
    assert down.self_efficacy < 0.5
    assert down.self_efficacy == pytest.approx(0.5 - 0.25 * 0.5)


def test_update_state_partial_pct_scales_failure_penalty() -> None:
    half = update_state(_state(self_efficacy=0.5), completed=False, partial_pct=0.5)
    assert half.self_efficacy == pytest.approx(0.5 + 0.15 * 0.5 * 0.5 - 0.25 * 0.5 * 0.5)
    full_fail = update_state(_state(self_efficacy=0.5), completed=False, partial_pct=0.0)
    assert full_fail.self_efficacy < half.self_efficacy


def test_update_state_self_efficacy_ignored_without_completed_flag() -> None:
    new = update_state(_state(self_efficacy=0.5), partial_pct=0.5)
    assert new.self_efficacy == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# replan_decision
# --------------------------------------------------------------------------- #


def test_replan_none_on_track() -> None:
    decision = replan_decision([0.8, 0.75], 0.2)
    assert (decision.decision, decision.reason_code) == ("none", "on_track")


def test_replan_local_repair_low_completion_2d() -> None:
    decision = replan_decision([0.5, 0.5], 0.2)
    assert (decision.decision, decision.reason_code) == ("local_repair", "low_completion_2d")


def test_replan_local_repair_duration_bias_high() -> None:
    decision = replan_decision([0.8], 0.6)
    assert (decision.decision, decision.reason_code) == ("local_repair", "duration_bias_high")


def test_replan_full_replan_5d() -> None:
    decision = replan_decision([0.3, 0.2, 0.35, 0.1, 0.3], 0.1)
    assert (decision.decision, decision.reason_code) == ("full_replan", "low_completion_5d")


def test_replan_full_replan_takes_precedence_over_local_repair() -> None:
    decision = replan_decision([0.3, 0.3], 0.9)  # also low-2d and high bias
    assert decision.decision == "full_replan"


def test_replan_pads_with_oldest_when_fewer_than_five() -> None:
    decision = replan_decision([0.3], 0.1)
    assert (decision.decision, decision.reason_code) == ("full_replan", "low_completion_5d")


def test_replan_empty_is_on_track() -> None:
    decision = replan_decision([], 0.9)
    assert (decision.decision, decision.reason_code) == ("none", "on_track")


# --------------------------------------------------------------------------- #
# should_prompt
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("prompts_24h", "in_focus_block", "fatigue", "expected"),
    [
        (0, False, 0.5, "send"),
        (2, False, 0.79, "send"),
        (3, False, 0.5, "defer"),
        (0, True, 0.5, "defer"),
        (0, False, 0.8, "defer"),
        (5, True, 0.9, "defer"),
    ],
)
def test_should_prompt_matrix(
    prompts_24h: int, in_focus_block: bool, fatigue: float, expected: str
) -> None:
    assert should_prompt(prompts_24h, in_focus_block, fatigue) == expected


# --------------------------------------------------------------------------- #
# profile_prompt_json
# --------------------------------------------------------------------------- #


def test_profile_prompt_json_keys() -> None:
    profile = UserProfileData(mbti_type="INTP", identity="大三学生")
    state = init_state(profile)
    payload = profile_prompt_json(profile, state)
    assert set(payload) == _PROMPT_KEYS
    assert payload["mbti_type"] == "INTP"
    assert payload["identity"] == "大三学生"
    assert payload["duration_factor"] == state.duration_factor
    assert payload["update_count"] == 0
    assert isinstance(payload["preferred_time_slots"], dict)


def test_profile_prompt_json_skips_none_identity() -> None:
    profile = UserProfileData(mbti_type="ENTP", identity=None)
    payload = profile_prompt_json(profile, init_state(profile))
    assert set(payload) == _PROMPT_KEYS - {"identity"}
    assert "identity" not in payload


# --------------------------------------------------------------------------- #
# frozen models
# --------------------------------------------------------------------------- #


def test_user_state_is_frozen() -> None:
    state = _state()
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.duration_factor = 2.0  # type: ignore[misc]


def test_user_profile_is_frozen() -> None:
    profile = UserProfileData(mbti_type="INTP")
    with pytest.raises(dataclasses.FrozenInstanceError):
        profile.mbti_type = "ENTP"  # type: ignore[misc]
