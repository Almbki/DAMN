"""Application DTOs for the agent flows."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.schemas import PreviewPayload
from app.application.dto.plan import PlanDetail
from app.ml.base import AdjustmentRoute, AdjustmentSeverity


def _warnings_from_state(state: dict) -> list[str]:
    """Human-readable warnings for the API from the run's recorded errors."""
    warnings: list[str] = []
    for error in state.get("errors") or []:
        kind = getattr(error, "kind", "error")
        message = getattr(error, "message", str(error))
        warnings.append(f"{kind}: {message}")
    return warnings


class PreviewResult(BaseModel):
    """Outcome of ``POST /plans/preview`` - the paused preview.

    ``degraded`` is true when the run continued with a fallback (no user
    history, LLM unavailable, context build failure). It is never silent: the
    client sees it, and the warnings say why.
    """

    thread_id: str
    preview: PreviewPayload
    goals_persisted: int = 0
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)


class ConfirmResult(BaseModel):
    """Outcome of confirming a preview."""

    detail: PlanDetail
    #: Set only when the graph paused again instead of finalising (should not
    #: happen on confirm, but the Service must not assume).
    pending_preview: PreviewPayload | None = None
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)


class AdjustPreviewResult(BaseModel):
    """Outcome of a preview adjustment.

    Either another preview is returned (budget left) or the graph finalised the
    plan because the adjustment budget was exhausted.
    """

    thread_id: str
    preview: PreviewPayload | None = None
    budget_exhausted: bool = False
    plan_id: int | None = None
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)


class FeedbackCycleOutcome(BaseModel):
    """Outcome of a feedback-driven agent run."""

    route: AdjustmentRoute = AdjustmentRoute.NO_CHANGE
    severity: AdjustmentSeverity = AdjustmentSeverity.NONE
    reasons: list[str] = Field(default_factory=list)
    source: str = "fallback"
    plan_id: int | None = None
    new_plan_id: int | None = None
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)


__all__ = [
    "AdjustPreviewResult",
    "ConfirmResult",
    "FeedbackCycleOutcome",
    "PreviewResult",
    "_warnings_from_state",
]
