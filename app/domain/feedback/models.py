"""Adjustment decision contract (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AdjustmentRoute(StrEnum):
    NO_CHANGE = "NO_CHANGE"
    MICRO_ADJUST = "MICRO_ADJUST"
    FULL_REPLAN = "FULL_REPLAN"


class AdjustmentSeverity(StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True, slots=True)
class AdjustmentDecision:
    """Deterministic feedback -> route decision.

    ``source`` is always truthful: ``policy:deterministic`` when computed from
    observed feedback, ``fallback:no_data`` when there is nothing to act on.
    """

    route: AdjustmentRoute = AdjustmentRoute.NO_CHANGE
    severity: AdjustmentSeverity = AdjustmentSeverity.NONE
    confidence: float = 0.0
    reasons: tuple[str, ...] = ()
    recommended_action: str | None = None
    predicted_parameters: dict[str, float] = field(default_factory=dict)
    source: str = "policy:deterministic"


__all__ = ["AdjustmentDecision", "AdjustmentRoute", "AdjustmentSeverity"]