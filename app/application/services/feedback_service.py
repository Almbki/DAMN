"""Feedback service: daily check-in submission and history.

After persisting the check-in the service runs the agent feedback cycle
(graph B): ML prediction -> adjustment router -> NO_CHANGE / MICRO_ADJUST /
FULL_REPLAN. Cooldown (``ReplanEligibility``) gates **manual** replans; the
feedback-driven route is bounded by the adjustment policy instead (it needs
elapsed days plus a low completion rate before it escalates to a full replan).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.dto.feedback import FeedbackSubmitResult
from app.application.exceptions import NotFoundError, PermissionDeniedError
from app.domain.models import Feedback
from app.infrastructure.database.repositories import (
    FeedbackRepository,
    PlanRepository,
    TaskRepository,
)


class FeedbackService:
    def __init__(
        self,
        session: Session,
        *,
        replan_service=None,
        plan_service=None,
        memory_service=None,
        profile_service=None,
    ) -> None:
        self._session = session
        self._feedback = FeedbackRepository(session)
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)
        self._replan_service = replan_service
        self._plan_service = plan_service
        self._memory_service = memory_service
        self._profile_service = profile_service

    def submit_feedback(
        self, user_id: int, plan_id: int, feedback: Feedback
    ) -> FeedbackSubmitResult:
        plan = self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError("plan not found")
        if plan.user_id != user_id:
            raise PermissionDeniedError("plan belongs to another user")

        payload = feedback.model_copy(update={"user_id": user_id, "plan_id": plan_id})
        saved = self._feedback.create(payload)
        self._session.commit()

        # Consolidate what we just learned into persisted memory (semantic /
        # episodic / procedural), so the next planning run reads it back.
        self._refresh_memory(user_id)
        # ... and into the adaptive portrait state (EWMA).
        self._update_profile_state(user_id, saved)

        eligibility = None
        if self._replan_service is not None:
            eligibility = self._replan_service.check_eligibility(user_id, plan_id)

        adjustment = None
        if self._plan_service is not None:
            outcome = self._plan_service.process_feedback_cycle(
                user_id, plan_id, note=saved.free_text
            )
            adjustment = outcome
            if outcome.new_plan_id is not None and self._replan_service is not None:
                eligibility = self._replan_service.check_eligibility(
                    user_id, outcome.new_plan_id
                )

        return FeedbackSubmitResult(
            feedback=saved,
            replan_triggered=bool(adjustment and adjustment.new_plan_id),
            replan_plan_id=adjustment.new_plan_id if adjustment else None,
            replan_eligibility=eligibility,
            adjustment=adjustment,
        )

    def list_feedback(self, user_id: int, plan_id: int) -> list[Feedback]:
        plan = self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError("plan not found")
        if plan.user_id != user_id:
            raise PermissionDeniedError("plan belongs to another user")
        return self._feedback.list_by_plan(plan_id)

    def _refresh_memory(self, user_id: int) -> None:
        """Update persisted memory; never let it break a feedback submission."""
        service = self._memory_service
        if service is None:
            from app.application.services.memory_service import MemoryService

            service = MemoryService(self._session)
        try:
            service.refresh(user_id)
        except Exception:  # noqa: BLE001 - memory is best-effort, feedback is the record
            self._session.rollback()

    def _update_profile_state(self, user_id: int, feedback: Feedback) -> None:
        """Feed the check-in through the portrait EWMA; best-effort only."""
        service = self._profile_service
        if service is None:
            from app.application.services.profile_service import ProfileService

            service = ProfileService(self._session)
        try:
            rate = feedback.completion_rate or 0.0
            service.update_from_feedback(
                user_id,
                completed=rate >= 0.999,
                partial_pct=rate,
                energy_after=feedback.energy_level,
                stress_after=feedback.stress_level,
            )
        except Exception:  # noqa: BLE001 - the feedback row is the record of truth
            self._session.rollback()
