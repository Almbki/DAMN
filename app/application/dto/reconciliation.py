"""DTOs for deterministic execution reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.models.enums import FeedbackObligationStatus


@dataclass(frozen=True)
class FeedbackObligation:
    """One unresolved (or resolved) user + execution-date feedback debt."""

    execution_date: date
    status: FeedbackObligationStatus
    is_retrospective: bool
    #: Plan the UI should POST the check-in against (the day's plan when known).
    plan_id: int | None = None


@dataclass(frozen=True)
class ReconciliationResult:
    """Outcome of reconciling one user's execution lifecycle."""

    as_of_date: date
    overdue_task_ids: tuple[int, ...] = ()
    missed_task_ids: tuple[int, ...] = ()
    pending_feedback_dates: tuple[date, ...] = ()
