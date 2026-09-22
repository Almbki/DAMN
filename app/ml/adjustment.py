"""Adjustment predictors.

Two implementations, neither is a trained model:

* :class:`RuleBasedAdjustmentPredictor` - deterministic rule fallback used when
  no ML model is available. Always reports ``source="fallback:rule"``.
* :class:`MockAdjustmentPredictor` - test double that returns a fixed route so
  every branch of the adjustment router can be exercised.

The real model (LightGBM / sklearn / ...) only has to implement
:class:`~app.ml.base.AdjustmentPredictor` and be injected into ``PredictorSet``.
"""

from __future__ import annotations

from statistics import mean

from app.ml.base import (
    AdjustmentPrediction,
    AdjustmentRequest,
    AdjustmentRoute,
    AdjustmentSeverity,
)

#: Completion-rate thresholds that separate the three routes.
_NO_CHANGE_THRESHOLD = 0.8
_MICRO_ADJUST_THRESHOLD = 0.5
#: How many recent check-ins the fallback rule looks at.
_WINDOW = 7
#: Minimum number of check-ins before a FULL_REPLAN is credible. A single bad
#: day is noise: escalate to a light adjustment, not to a rebuild.
_MIN_SIGNALS_FOR_REPLAN = 2


class RuleBasedAdjustmentPredictor:
    """Deterministic fallback: route purely from recent completion/stress/energy.

    This is **not** machine learning; it exists so the feedback loop can run
    before the ML model is delivered, and it is always labelled
    ``source="fallback:rule"``.
    """

    name = "rule-based-adjustment-fallback"

    def predict_adjustment(self, request: AdjustmentRequest) -> AdjustmentPrediction:
        signals = request.recent_feedback[-_WINDOW:]
        if not signals:
            return AdjustmentPrediction(
                route=AdjustmentRoute.NO_CHANGE,
                severity=AdjustmentSeverity.NONE,
                confidence=0.3,
                reasons=["no recent feedback to analyse"],
                recommended_action="keep the current plan",
                source="fallback:rule",
            )

        rates = [signal.completion_rate for signal in signals]
        avg_rate = mean(rates)
        stress = [s.stress_level for s in signals if s.stress_level is not None]
        energy = [s.energy_level for s in signals if s.energy_level is not None]
        avg_stress = mean(stress) if stress else 5.0
        avg_energy = mean(energy) if energy else 5.0

        reasons = [
            f"avg completion over last {len(signals)} check-in(s): {avg_rate:.2f}",
            f"avg stress: {avg_stress:.1f}, avg energy: {avg_energy:.1f}",
        ]
        parameters: dict[str, float] = {"recent_completion_rate": round(avg_rate, 3)}

        if avg_rate >= _NO_CHANGE_THRESHOLD and avg_stress < 7.0 and avg_energy >= 4.0:
            return AdjustmentPrediction(
                route=AdjustmentRoute.NO_CHANGE,
                severity=AdjustmentSeverity.NONE,
                confidence=0.5,
                predicted_parameters=parameters,
                reasons=reasons + ["user is keeping up with the plan"],
                recommended_action="keep the current plan",
                source="fallback:rule",
            )

        if avg_rate >= _MICRO_ADJUST_THRESHOLD:
            severity = (
                AdjustmentSeverity.HIGH
                if (avg_stress >= 7.0 or avg_energy < 4.0)
                else AdjustmentSeverity.MEDIUM
            )
            parameters["suggested_daily_limit_factor"] = 0.85
            return AdjustmentPrediction(
                route=AdjustmentRoute.MICRO_ADJUST,
                severity=severity,
                confidence=0.5,
                predicted_parameters=parameters,
                reasons=reasons + ["slightly behind; lighten the daily load"],
                recommended_action="reschedule / trim the current plan without a full replan",
                source="fallback:rule",
            )

        parameters["suggested_daily_limit_factor"] = 0.7
        if len(signals) < _MIN_SIGNALS_FOR_REPLAN:
            # Not enough evidence to justify rebuilding the whole plan.
            parameters["suggested_daily_limit_factor"] = 0.85
            return AdjustmentPrediction(
                route=AdjustmentRoute.MICRO_ADJUST,
                severity=AdjustmentSeverity.HIGH,
                confidence=0.35,
                predicted_parameters=parameters,
                reasons=reasons
                + [
                    "below target, but only "
                    f"{len(signals)} check-in(s) - lightening the load first"
                ],
                recommended_action="reschedule / trim the current plan, then re-evaluate",
                source="fallback:rule",
            )

        return AdjustmentPrediction(
            route=AdjustmentRoute.FULL_REPLAN,
            severity=AdjustmentSeverity.HIGH,
            confidence=0.6,
            predicted_parameters=parameters,
            reasons=reasons + ["consistently below target; the plan needs rebuilding"],
            recommended_action="rebuild the plan with a lower daily load",
            source="fallback:rule",
        )


class MockAdjustmentPredictor:
    """Test double returning a caller-fixed prediction (never real ML)."""

    name = "mock-adjustment"

    def __init__(
        self,
        route: AdjustmentRoute = AdjustmentRoute.NO_CHANGE,
        *,
        severity: AdjustmentSeverity = AdjustmentSeverity.NONE,
        confidence: float = 0.9,
        reasons: list[str] | None = None,
        recommended_action: str | None = None,
        predicted_parameters: dict[str, float] | None = None,
    ) -> None:
        self.route = route
        self.severity = severity
        self.confidence = confidence
        self.reasons = reasons or [f"mock prediction: {route.value}"]
        self.recommended_action = recommended_action
        self.predicted_parameters = predicted_parameters or {}

    def predict_adjustment(self, request: AdjustmentRequest) -> AdjustmentPrediction:
        return AdjustmentPrediction(
            route=self.route,
            severity=self.severity,
            confidence=self.confidence,
            predicted_parameters=dict(self.predicted_parameters),
            reasons=list(self.reasons),
            recommended_action=self.recommended_action,
            source="mock",
        )
