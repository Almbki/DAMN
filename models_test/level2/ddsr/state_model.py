"""Two-stage DDSR-V1 state model: prediction, correction, tomorrow prior.

Stage 1 (prediction):  S_d^- = rho * S_(d-1)^+ + (1-rho) * population_mean
                       sigma_d^- = sqrt(rho^2 * sigma_(d-1)^+^2 + q)
Stage 2 (correction):  p(x | evidence, logs) ∝ prior(x) * product(likelihoods)

The implementation is a small grid Bayes filter.  It is deliberately simple:
no deep sequence model, no invented literature coefficients, and no online
personalization in V1.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from .config import STATE_KEYS, DDSRConfig
from .schemas import (
    BehavioralIndicators,
    Direction,
    EvidenceAvailability,
    EvidenceItem,
    StateName,
)


@dataclass(frozen=True)
class PriorState:
    value: dict[str, float]
    uncertainty: dict[str, float]
    source: str
    gap_days: int = 0


@dataclass(frozen=True)
class CorrectionResult:
    posterior: dict[str, float]
    uncertainty: dict[str, float]
    evidence_counts: dict[str, int]
    evidence_availability: dict[str, EvidenceAvailability]
    conflict_states: list[StateName]


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clip_sd(value: float, config: DDSRConfig) -> float:
    return _clip(value, config.uncertainty_floor, config.uncertainty_ceiling)


def cold_start(config: DDSRConfig) -> PriorState:
    """Transparent neutral population prior for Day 1; not individualized."""
    return PriorState(
        value={state: float(config.cold_start_mean[state]) for state in STATE_KEYS},
        uncertainty={state: float(config.cold_start_sd) for state in STATE_KEYS},
        source="cold_start_population_prior",
        gap_days=0,
    )


def predict_next(
    posterior: Mapping[str, float],
    uncertainty: Mapping[str, float],
    config: DDSRConfig,
    steps: int = 1,
    source: str = "transition_from_previous_posterior",
) -> PriorState:
    """Apply the conservative AR(1)-style transition ``steps`` times.

    ``steps`` is the calendar gap in days.  Repeating the transition decays the
    mean toward the population neutral point and increases uncertainty, which
    prevents both state lock and uncertainty explosion.
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    mu = {state: _clip(float(posterior[state]), 0.0, 1.0) for state in STATE_KEYS}
    sd = {
        state: _clip_sd(float(uncertainty[state]), config) for state in STATE_KEYS
    }
    for _ in range(steps):
        for state in STATE_KEYS:
            rho = float(config.persistence_rho[state])
            population = float(config.cold_start_mean[state])
            mu[state] = _clip(
                rho * mu[state] + (1.0 - rho) * population, 0.0, 1.0
            )
            variance = (rho * sd[state]) ** 2 + float(
                config.process_noise_sd[state]
            ) ** 2
            sd[state] = _clip_sd(math.sqrt(variance), config)
    return PriorState(value=mu, uncertainty=sd, source=source, gap_days=steps)


def _normalise(log_weights: list[float]) -> list[float]:
    maximum = max(log_weights)
    weights = [math.exp(value - maximum) for value in log_weights]
    total = sum(weights)
    if total <= 0.0 or not math.isfinite(total):
        raise ValueError("non-finite posterior weights")
    return [weight / total for weight in weights]


def _summary(
    weights: list[float], grid: list[float], config: DDSRConfig
) -> tuple[float, float]:
    mean = sum(weight * x for weight, x in zip(weights, grid, strict=True))
    variance = sum(
        weight * (x - mean) ** 2
        for weight, x in zip(weights, grid, strict=True)
    )
    return _clip(mean, 0.0, 1.0), _clip_sd(math.sqrt(max(0.0, variance)), config)


def _evidence_sign(item: EvidenceItem) -> int:
    return 1 if item.direction is Direction.INCREASE else -1


def correct(
    prior: PriorState,
    evidence: list[EvidenceItem],
    indicators: BehavioralIndicators,
    config: DDSRConfig,
) -> CorrectionResult:
    """Combine prior, reflection evidence, and task-log indicators.

    Only three mappings are allowed:

    * fatigue / stress / self-efficacy evidence -> their own state;
    * goal attainment -> self-efficacy (direction from Wäschle et al. 2014);
    * everything else (procrastination, interruption) stays a behavioural
      indicator and never changes a state.
    """
    grid = config.grid
    log_weights: dict[str, list[float]] = {}
    for state in STATE_KEYS:
        mean = float(prior.value[state])
        sd = _clip_sd(float(prior.uncertainty[state]), config)
        log_weights[state] = [
            -0.5 * ((x - mean) / sd) ** 2 for x in grid
        ]

    directions: dict[str, set[int]] = {state: set() for state in STATE_KEYS}
    counts: dict[str, int] = {state: 0 for state in STATE_KEYS}

    for item in evidence:
        state = item.target_state
        if state is None:
            continue
        key = state.value
        counts[key] += 1
        sign = _evidence_sign(item)
        directions[key].add(sign)
        strength = float(config.strength_weights[item.strength.value])
        coefficient = config.evidence_sharpness * strength * sign
        log_weights[key] = [
            log_weight + coefficient * (x - 0.5)
            for log_weight, x in zip(log_weights[key], grid, strict=True)
        ]

    # Task-log goal attainment is a weak self-efficacy observation.  A value of
    # exactly 0.5 contributes no tilt; high attainment favors high self-efficacy.
    goal = indicators.goal_attainment.value
    if goal is not None:
        coefficient = (
            config.evidence_sharpness
            * config.goal_attainment_weight
            * (float(goal) - 0.5)
        )
        log_weights[StateName.SELF_EFFICACY.value] = [
            log_weight + coefficient * (x - 0.5)
            for log_weight, x in zip(
                log_weights[StateName.SELF_EFFICACY.value], grid, strict=True
            )
        ]

    posterior: dict[str, float] = {}
    uncertainty: dict[str, float] = {}
    for state in STATE_KEYS:
        weights = _normalise(log_weights[state])
        mean, sd = _summary(weights, grid, config)
        posterior[state] = mean
        uncertainty[state] = sd

    conflict_states = [
        StateName(state)
        for state in STATE_KEYS
        if len(directions[state]) > 1
    ]

    availability: dict[str, EvidenceAvailability] = {}
    for state in STATE_KEYS:
        has_reflection = counts[state] > 0
        if state == StateName.SELF_EFFICACY.value:
            has_task = goal is not None
            if has_reflection and has_task:
                availability[state] = EvidenceAvailability.REFLECTION_AND_TASK_LOG
            elif has_reflection:
                availability[state] = EvidenceAvailability.REFLECTION_ONLY
            elif has_task:
                availability[state] = EvidenceAvailability.TASK_LOG_ONLY
            else:
                availability[state] = EvidenceAvailability.NONE
        else:
            availability[state] = (
                EvidenceAvailability.REFLECTION_ONLY
                if has_reflection
                else EvidenceAvailability.NONE
            )

    return CorrectionResult(
        posterior=posterior,
        uncertainty=uncertainty,
        evidence_counts=counts,
        evidence_availability=availability,
        conflict_states=conflict_states,
    )


def prediction_error(
    posterior: Mapping[str, float],
    prior: PriorState,
) -> tuple[dict[str, float], dict[str, float]]:
    raw = {state: float(posterior[state]) - float(prior.value[state]) for state in STATE_KEYS}
    standardized = {
        state: raw[state] / float(prior.uncertainty[state])
        if prior.uncertainty[state] > 0
        else 0.0
        for state in STATE_KEYS
    }
    return raw, standardized
