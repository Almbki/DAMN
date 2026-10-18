"""Feedback-driven replan policy (pure, stdlib only).

Daily feedback is *always* persisted. This policy decides whether the saved
check-in justifies running the feedback agent cycle at all, and whether that
cycle should aim for a micro adjustment or a full replan.

Design rules
------------
* Completion rate on its own never triggers a replan. Historical completion is
  only a portrait input, and the portrait is gated by current pressure
  (stress/energy) or a high duration bias.
* Current pressure is the primary signal: high stress / low energy is enough
  for a micro adjustment; severe pressure only escalates to a full replan when
  completion is low or the duration bias is high.
* Free text is context for the prompt, never a route override. Explicit manual
  replans (``REPLAN_REQUEST``) bypass this policy at the service/API entrypoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Route = str  # Literal["none", "micro_adjust", "full_replan"]
Pressure = str  # Literal["none", "high", "severe"]


@dataclass(frozen=True, slots=True)
class FeedbackReplanDecision:
    """Outcome of the feedback replan policy."""

    route: Route
    reason: str
    pressure: Pressure
    signals: dict = field(default_factory=dict)


def decide_feedback_replan(
    *,
    stress: float | None,
    energy: float | None,
    completion_rate: float,
    duration_bias: float,
    portrait_decision: str,
    stress_high: float = 7.0,
    energy_low: float = 4.0,
    stress_severe: float = 8.0,
    energy_critical: float = 3.0,
    duration_bias_high: float = 0.50,
) -> FeedbackReplanDecision:
    """Decide whether the current check-in should trigger a replan.

    ``stress`` / ``energy`` are the check-in's 0..10 values (``None`` when the
    user did not report them). ``portrait_decision`` is the existing portrait
    verdict (``"full_replan"`` / ``"local_repair"`` / ``"none"``).

    The returned route is one of ``"none"``, ``"micro_adjust"`` or
    ``"full_replan"``. ``pressure`` reports the current stress/energy band;
    note it can be ``"none"`` while the route is ``micro_adjust`` when only the
    duration bias is high.
    """
    pressure_high = (stress is not None and stress >= stress_high) or (
        energy is not None and energy <= energy_low
    )
    pressure_severe = (stress is not None and stress >= stress_severe) or (
        energy is not None and energy <= energy_critical
    )
    pressure: Pressure = (
        "severe" if pressure_severe else "high" if pressure_high else "none"
    )

    duration_bias_pressure = duration_bias > duration_bias_high
    # Portrait history (completion rates) is evidence, not a trigger: it only
    # counts while the user is under pressure now or is consistently overrunning.
    portrait_gate_open = pressure_high or duration_bias_pressure
    portrait_full = portrait_decision == "full_replan" and portrait_gate_open
    portrait_local = portrait_decision == "local_repair" and portrait_gate_open

    severe_escalation = pressure_severe and (
        completion_rate < 0.6 or duration_bias_pressure
    )

    reasons: list[str] = []
    if portrait_full:
        reasons.append("portrait history indicates a full replan under current pressure")
    if pressure_severe:
        reasons.append("severe stress/energy pressure")
    elif pressure_high:
        reasons.append("high stress or low energy")
    if duration_bias_pressure:
        reasons.append(f"duration bias {duration_bias:.2f} > {duration_bias_high:.2f}")
    if severe_escalation:
        reasons.append(f"completion rate {completion_rate:.2f} under severe pressure")

    if portrait_full or severe_escalation:
        route = "full_replan"
    elif pressure_high or duration_bias_pressure or portrait_local:
        route = "micro_adjust"
    else:
        route = "none"

    if route == "none":
        reason = "no pressure signal and completion history alone does not trigger a replan"
    else:
        reason = "; ".join(reasons)

    return FeedbackReplanDecision(
        route=route,
        reason=reason,
        pressure=pressure,
        signals={
            "stress": stress,
            "energy": energy,
            "completion_rate": completion_rate,
            "duration_bias": duration_bias,
            "portrait_decision": portrait_decision,
            "pressure_high": pressure_high,
            "pressure_severe": pressure_severe,
            "duration_bias_high": duration_bias_high,
            "portrait_gate_open": portrait_gate_open,
        },
    )


__all__ = ["FeedbackReplanDecision", "decide_feedback_replan"]
