"""Pure user-profile engine: type resolution, state init, predictors, updates.

All functions are pure (no I/O, no FastAPI/SQLAlchemy). Formulas follow
``ideas and structures/Prompts/画像.md`` §2-4 and ``docs/fin/核心闭环.md``
环节 1; every coefficient is an 【工程】 default pending calibration.

MBTI percentage-weighting rule (画像.md 可选 6)
----------------------------------------------
``init_state`` first resolves the majority-letter type (``resolve_mbti_type``),
then, per dimension ``d`` with weight ``w`` in ``profile.mbti_dims`` (clamped
to [0, 1]), blends every numeric template field as::

    value = w * template[resolved] + (1 - w) * template[flipped]

where ``resolved`` carries the dimension's majority letter and ``flipped`` is
``resolved`` with that letter switched. Each dimension is applied independently
against the original resolved template (no sequential compounding).
``preferred_time_slots`` is non-numeric and always comes from the
majority-resolved type.
"""

from __future__ import annotations

import dataclasses

from app.domain.profile.mbti_templates import (
    DIMENSION_LETTERS,
    MBTI_DIMENSIONS,
    MBTI_TEMPLATES,
    TYPE_MULTIPLIER,
    VALID_MBTI_TYPES,
)
from app.domain.profile.models import (
    CompletionEstimate,
    DurationEstimate,
    ReplanDecision,
    UserProfileData,
    UserStateData,
)

#: Numeric (blendable) template fields - every template field except the
#: non-numeric ``preferred_time_slots``.
_NUMERIC_FIELDS: tuple[str, ...] = (
    "duration_factor",
    "completion_prob",
    "stress_baseline",
    "energy_drain_rate",
    "proactive_score",
    "procrastination_tendency",
    "stress_response",
)

#: EWMA smoothing factor (画像.md §3, 【工程】).
_EWMA_ALPHA = 0.3
#: Self-efficacy event gains (画像.md §3 / RO-2 §4.4.3, 【工程】).
_EFFICACY_GAIN = 0.15
_EFFICACY_LOSS = 0.25


def _flip_letter(mbti_type: str, dim: str) -> str:
    """Return ``mbti_type`` with the letter at dimension ``dim`` flipped."""
    idx = MBTI_DIMENSIONS.index(dim)
    pair = DIMENSION_LETTERS[dim]
    flipped = pair[1] if mbti_type[idx] == pair[0] else pair[0]
    return mbti_type[:idx] + flipped + mbti_type[idx + 1 :]


def resolve_mbti_type(profile: UserProfileData) -> str:
    """Resolve the effective 16-type code (or ``"_default"``).

    1. An explicit, valid ``mbti_type`` (case-insensitive) is the base;
       otherwise the base is the ``_default`` placeholder.
    2. For every dimension present in ``mbti_dims``, the majority letter
       (weight >= 0.5 -> first letter of the pair, else second) overrides the
       corresponding position of the base type.
    3. The result is returned only if it is one of the 16 valid types,
       otherwise ``"_default"``.
    """
    base: str = "_default"
    if profile.mbti_type:
        candidate = profile.mbti_type.strip().upper()
        if candidate in VALID_MBTI_TYPES:
            base = candidate

    letters: list[str] = list("XXXX") if base == "_default" else list(base)
    for idx, dim in enumerate(MBTI_DIMENSIONS):
        weight = (profile.mbti_dims or {}).get(dim)
        if weight is None:
            continue
        majority = DIMENSION_LETTERS[dim][0] if weight >= 0.5 else DIMENSION_LETTERS[dim][1]
        letters[idx] = majority

    resolved = "".join(letters)
    return resolved if resolved in VALID_MBTI_TYPES else "_default"


def init_state(profile: UserProfileData) -> UserStateData:
    """Initialise ``UserStateData`` from the MBTI template.

    Hard classification: with no usable ``mbti_dims`` the state is an exact
    copy of the resolved type's template (or ``_default``). With ``mbti_dims``,
    numeric template fields are percentage-weighted per the blending rule
    documented in the module docstring; ``preferred_time_slots`` is always
    taken from the majority-resolved type. Dynamic fields start at the
    template-neutral 0.5 and ``update_count`` is 0.
    """
    resolved = resolve_mbti_type(profile)
    base_tmpl = MBTI_TEMPLATES[resolved]
    values: dict[str, float] = {f: base_tmpl[f] for f in _NUMERIC_FIELDS}

    for dim in MBTI_DIMENSIONS:
        weight = (profile.mbti_dims or {}).get(dim)
        if weight is None:
            continue
        weight = max(0.0, min(1.0, float(weight)))
        variant = MBTI_TEMPLATES[_flip_letter(resolved, dim)]
        for f in _NUMERIC_FIELDS:
            values[f] = weight * base_tmpl[f] + (1.0 - weight) * variant[f]

    return UserStateData(
        duration_factor=values["duration_factor"],
        completion_prob=values["completion_prob"],
        stress_baseline=values["stress_baseline"],
        energy_drain_rate=values["energy_drain_rate"],
        proactive_score=values["proactive_score"],
        procrastination_tendency=values["procrastination_tendency"],
        preferred_time_slots=dict(base_tmpl["preferred_time_slots"]),
        stress_response=values["stress_response"],
        state_energy=0.5,
        state_fatigue=0.5,
        self_efficacy=0.5,
        update_count=0,
    )


def predict_duration(
    theoretical_min: float, task_type: str, state: UserStateData
) -> DurationEstimate:
    """Predict q50/q80 duration (画像.md §3, 【工程】 coefficients).

    ``base = theoretical_min * TYPE_MULTIPLIER[task_type]`` (unknown -> 1.0),
    ``fatigue_factor = 1 + 0.30*(fatigue - 0.5)``,
    ``energy_factor  = 1 - 0.20*(energy  - 0.5)``,
    ``q50 = base * duration_factor * fatigue_factor * energy_factor``,
    ``q80 = q50 * 1.25``. ``degraded`` while ``update_count < 3``.
    """
    base = theoretical_min * TYPE_MULTIPLIER.get(task_type, 1.0)
    fatigue_factor = 1.0 + 0.30 * (state.state_fatigue - 0.5)
    energy_factor = 1.0 - 0.20 * (state.state_energy - 0.5)
    q50 = base * state.duration_factor * fatigue_factor * energy_factor
    return DurationEstimate(q50=q50, q80=q50 * 1.25, degraded=state.update_count < 3)


def predict_completion(
    state: UserStateData, recent_completion_rate_7d: float | None = None
) -> CompletionEstimate:
    """Predict task completion probability (画像.md §3).

    Cold start (``update_count == 0`` or no 7d rate) returns the template prior
    ``state.completion_prob``; otherwise a 50/50 blend with the observed 7d
    completion rate. The result is clamped to [0.05, 0.98] and flagged
    ``degraded`` while ``update_count < 3``.
    """
    if state.update_count == 0 or recent_completion_rate_7d is None:
        prob = state.completion_prob
    else:
        prob = 0.5 * state.completion_prob + 0.5 * recent_completion_rate_7d
    prob = max(0.05, min(0.98, prob))
    return CompletionEstimate(prob=prob, degraded=state.update_count < 3)


def update_state(
    state: UserStateData,
    *,
    actual_min: float | None = None,
    theoretical_min: float | None = None,
    completed: bool | None = None,
    partial_pct: float | None = None,
    energy_after: float | None = None,
    stress_after: float | None = None,
) -> UserStateData:
    """Feedback-update the state with EWMA (alpha=0.3) and return a new one.

    Only fields with a present observation are updated:

    * ``duration_factor`` from ``actual_min/theoretical_min`` (skipped when
      ``theoretical_min`` is falsy/<= 0), ratio clamped to [0.5, 3.0];
    * ``state_energy``  <- EWMA(``energy_after``/10), repo 0-10 input scale;
    * ``state_fatigue`` <- EWMA(1 - ``energy_after``/10);
    * ``stress_baseline`` <- EWMA(``stress_after``/10);
    * ``self_efficacy`` via the event rule (only when ``completed`` is given):
      ``s = 1.0 if completed else (partial_pct or 0.0)``,
      ``SE += 0.15*s*(1-SE) - 0.25*(1-s)*SE``, clamped to [0, 1].

    The original ``state`` is untouched (dataclass is frozen); ``update_count``
    is always incremented by one.
    """
    duration_factor = state.duration_factor
    if actual_min is not None and theoretical_min and theoretical_min > 0:
        ratio = max(0.5, min(3.0, actual_min / theoretical_min))
        duration_factor = _EWMA_ALPHA * ratio + (1.0 - _EWMA_ALPHA) * state.duration_factor

    state_energy = state.state_energy
    state_fatigue = state.state_fatigue
    if energy_after is not None:
        energy_obs = max(0.0, min(1.0, energy_after / 10.0))
        state_energy = _EWMA_ALPHA * energy_obs + (1.0 - _EWMA_ALPHA) * state.state_energy
        state_fatigue = _EWMA_ALPHA * (1.0 - energy_obs) + (1.0 - _EWMA_ALPHA) * state.state_fatigue

    stress_baseline = state.stress_baseline
    if stress_after is not None:
        stress_obs = max(0.0, min(1.0, stress_after / 10.0))
        stress_baseline = _EWMA_ALPHA * stress_obs + (1.0 - _EWMA_ALPHA) * state.stress_baseline

    self_efficacy = state.self_efficacy
    if completed is not None:
        success = 1.0 if completed else (partial_pct or 0.0)
        se = (
            self_efficacy
            + _EFFICACY_GAIN * success * (1.0 - self_efficacy)
            - _EFFICACY_LOSS * (1.0 - success) * self_efficacy
        )
        self_efficacy = max(0.0, min(1.0, se))

    return dataclasses.replace(
        state,
        duration_factor=duration_factor,
        stress_baseline=stress_baseline,
        state_energy=state_energy,
        state_fatigue=state_fatigue,
        self_efficacy=self_efficacy,
        update_count=state.update_count + 1,
    )


def _pad_oldest(rates: list[float], length: int = 5) -> list[float]:
    """Return the last ``length`` rates, left-padding with the oldest value."""
    if len(rates) >= length:
        return rates[-length:]
    return [rates[0]] * (length - len(rates)) + rates


def replan_decision(
    completion_rates_3d: list[float], duration_bias: float
) -> ReplanDecision:
    """Decide whether/how to replan (画像.md §4). Most recent day last.

    Precedence: ``full_replan`` > ``local_repair`` > ``none``.

    * 5 consecutive (left-padded with the oldest rate when fewer are given)
      rates all ``< 0.40`` -> ``full_replan`` / ``low_completion_5d``;
    * the last two rates both ``< 0.60`` -> ``local_repair`` /
      ``low_completion_2d``;
    * ``duration_bias > 0.50`` -> ``local_repair`` / ``duration_bias_high``;
    * otherwise -> ``none`` / ``on_track``.
    """
    rates = list(completion_rates_3d)
    if not rates:
        return ReplanDecision(decision="none", reason_code="on_track")

    window = _pad_oldest(rates, 5)
    if all(r < 0.40 for r in window):
        return ReplanDecision(decision="full_replan", reason_code="low_completion_5d")

    if len(rates) >= 2 and rates[-1] < 0.60 and rates[-2] < 0.60:
        return ReplanDecision(decision="local_repair", reason_code="low_completion_2d")

    if duration_bias > 0.50:
        return ReplanDecision(decision="local_repair", reason_code="duration_bias_high")

    return ReplanDecision(decision="none", reason_code="on_track")


def should_prompt(prompts_24h: int, in_focus_block: bool, fatigue: float) -> str:
    """Should we nudge the user right now? ``"send"`` iff <3 prompts in 24h,
    not inside a focus block, and fatigue < 0.8; otherwise ``"defer"``."""
    if prompts_24h < 3 and not in_focus_block and fatigue < 0.8:
        return "send"
    return "defer"


def profile_prompt_json(profile: UserProfileData, state: UserStateData) -> dict:
    """JSON-serialisable portrait for 环节 2 prompt injection.

    Returns exactly the numeric portrait fields consumed by the plan-generation
    prompt. ``None`` profile fields are skipped.
    """
    payload: dict = {
        "mbti_type": resolve_mbti_type(profile),
        "duration_factor": state.duration_factor,
        "completion_prob": state.completion_prob,
        "self_efficacy": state.self_efficacy,
        "state_energy": state.state_energy,
        "state_fatigue": state.state_fatigue,
        "stress_baseline": state.stress_baseline,
        "procrastination_tendency": state.procrastination_tendency,
        "proactive_score": state.proactive_score,
        "preferred_time_slots": dict(state.preferred_time_slots),
        "update_count": state.update_count,
    }
    if profile.identity is not None:
        payload["identity"] = profile.identity
    return payload
