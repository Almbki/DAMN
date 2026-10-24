"""Deterministic adjustment policy (replaces the mock ML adjustment predictor).

This is a policy, not a model. It consumes *observed* check-in aggregates and
the Level 2 dynamic state (when available) and returns an explicit route. The
old statistical predictor and its test double are gone.

Rules (ported from the previous fallback, kept intentionally conservative):

* No recent feedback -> NO_CHANGE (there is nothing to act on).
* Good completion + low pressure -> NO_CHANGE.
* Mildly behind / high pressure -> MICRO_ADJUST with a smaller daily limit.
* Consistently behind with enough signals -> FULL_REPLAN.
* A single bad day never triggers a rebuild.
"""

from __future__ import annotations

from collections.abc import Sequence
from statistics import mean

from app.domain.feedback.models import AdjustmentDecision, AdjustmentRoute, AdjustmentSeverity

NO_CHANGE_THRESHOLD = 0.8
MICRO_ADJUST_THRESHOLD = 0.5
MIN_SIGNALS_FOR_REPLAN = 2
WINDOW = 7


def decide_adjustment(
    *,
    completion_rates: Sequence[float],
    stress_levels: Sequence[float] = (),
    energy_levels: Sequence[float] = (),
    state_fatigue: float | None = None,
    state_stress: float | None = None,
    state_self_efficacy: float | None = None,
) -> AdjustmentDecision:
    """Return the deterministic route for a feedback cycle."""
    rates = list(completion_rates)[-WINDOW:]
    if not rates:
        return AdjustmentDecision(
            route=AdjustmentRoute.NO_CHANGE,
            severity=AdjustmentSeverity.NONE,
            confidence=0.3,
            reasons=("no recent feedback to analyse",),
            recommended_action="keep the current plan",
            source="fallback:no_data",
        )

    avg_rate = mean(rates)
    stress = list(stress_levels)[-WINDOW:]
    energy = list(energy_levels)[-WINDOW:]
    avg_stress = mean(stress) if stress else 5.0
    avg_energy = mean(energy) if energy else 5.0

    reasons: list[str] = [
        f"avg completion over last {len(rates)} check-in(s): {avg_rate:.2f}",
        f"avg stress: {avg_stress:.1f}, avg energy: {avg_energy:.1f}",
    ]
    parameters: dict[str, float] = {"recent_completion_rate": round(avg_rate, 3)}

    # Level 2 observations are explanatory only; they do not invent a route on
    # their own (a bad day is not a plan failure).
    state_pressure = False
    if state_stress is not None or state_fatigue is not None:
        pressure = max(state_stress or 0.0, state_fatigue or 0.0)
        state_pressure = pressure >= 0.7
        parameters["level2_pressure"] = round(pressure, 3)
        reasons.append(f"level2 pressure {pressure:.2f}")
    if state_self_efficacy is not None:
        parameters["level2_self_efficacy"] = round(state_self_efficacy, 3)

    if (
        avg_rate >= NO_CHANGE_THRESHOLD
        and avg_stress < 7.0
        and avg_energy >= 4.0
        and not state_pressure
    ):
        return AdjustmentDecision(
            route=AdjustmentRoute.NO_CHANGE,
            severity=AdjustmentSeverity.NONE,
            confidence=0.5,
            reasons=tuple(reasons + ["user is keeping up with the plan"]),
            recommended_action="keep the current plan",
            predicted_parameters=parameters,
        )

    if avg_rate >= MICRO_ADJUST_THRESHOLD:
        severity = (
            AdjustmentSeverity.HIGH
            if (avg_stress >= 7.0 or avg_energy < 4.0 or state_pressure)
            else AdjustmentSeverity.MEDIUM
        )
        parameters["suggested_daily_limit_factor"] = 0.85
        return AdjustmentDecision(
            route=AdjustmentRoute.MICRO_ADJUST,
            severity=severity,
            confidence=0.5,
            reasons=tuple(reasons + ["slightly behind; lighten the daily load"]),
            recommended_action="reschedule / trim the current plan without a full replan",
            predicted_parameters=parameters,
        )

    parameters["suggested_daily_limit_factor"] = 0.7
    if len(rates) < MIN_SIGNALS_FOR_REPLAN:
        parameters["suggested_daily_limit_factor"] = 0.85
        return AdjustmentDecision(
            route=AdjustmentRoute.MICRO_ADJUST,
            severity=AdjustmentSeverity.HIGH,
            confidence=0.35,
            reasons=tuple(
                reasons
                + [
                    f"below target, but only {len(rates)} check-in(s) - "
                    "lightening the load first"
                ]
            ),
            recommended_action="reschedule / trim the current plan, then re-evaluate",
            predicted_parameters=parameters,
        )

    return AdjustmentDecision(
        route=AdjustmentRoute.FULL_REPLAN,
        severity=AdjustmentSeverity.HIGH,
        confidence=0.6,
        reasons=tuple(reasons + ["consistently below target; the plan needs rebuilding"]),
        recommended_action="rebuild the plan with a lower daily load",
        predicted_parameters=parameters,
    )


__all__ = [
    "MICRO_ADJUST_THRESHOLD",
    "MIN_SIGNALS_FOR_REPLAN",
    "NO_CHANGE_THRESHOLD",
    "WINDOW",
    "decide_adjustment",
]