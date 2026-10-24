"""Feedback service: daily check-in submission and history.

The check-in is **always** persisted first. Afterwards a pure policy
(:func:`app.domain.feedback.policy.decide_feedback_replan`) decides whether the
saved feedback justifies running the agent feedback cycle (graph B) at all:

* ``none``          -> record only; the plan is untouched
* ``micro_adjust``  -> run graph B (ML + router + scheduler/rules)
* ``full_replan``   -> run graph B (ML + router + planner)

The policy is driven by the check-in's stress/energy plus the portrait model
(duration bias and recent completion rates). Completion rate alone never
triggers a replan, and free text is prompt context only. Explicit manual
replans bypass this policy and still force ``FULL_REPLAN``.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.dto.feedback import FeedbackSubmitResult
from app.application.exceptions import NotFoundError, PermissionDeniedError
from app.core.config import get_settings
from app.domain.feedback.policy import (
    FeedbackReplanDecision,
    decide_feedback_replan,
)
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
    ) -> None:
        self._session = session
        self._feedback = FeedbackRepository(session)
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)
        self._replan_service = replan_service
        self._plan_service = plan_service

    def submit_feedback(
        self,
        user_id: int,
        plan_id: int,
        feedback: Feedback,
        *,
        defer_replan: bool = False,
    ) -> FeedbackSubmitResult:
        """Persist the check-in and (optionally) run the feedback cycle.

        ``defer_replan`` is used by the streaming API: the expensive agent cycle
        runs in a background job after this call returns, so only the check-in
        side effects happen here.
        """
        plan = self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError("plan not found")
        if plan.user_id != user_id:
            raise PermissionDeniedError("plan belongs to another user")

        payload = feedback.model_copy(
            update={
                "user_id": user_id,
                "plan_id": plan_id,
                # A check-in on a synthetic demo plan is synthetic provenance too.
                "data_origin": plan.data_origin,
            }
        )
        saved = self._feedback.create(payload)
        self._session.commit()

        # Consolidate what we just learned into persisted memory (semantic /
        # episodic / procedural), so the next planning run reads it back.
        self._refresh_memory(user_id)
        # ... and refresh the real Level 2 dynamic state from the new check-in.
        self._refresh_user_model(user_id)

        eligibility = None
        if self._replan_service is not None:
            eligibility = self._replan_service.check_eligibility(user_id, plan_id)

        decision = self._decide_replan(user_id, saved)

        adjustment = None
        if (
            not defer_replan
            and self._plan_service is not None
            and decision.route != "none"
        ):
            # Free text is context for the prompt only: it no longer sets
            # `user_adjustment`, so it cannot force a FULL_REPLAN by itself.
            outcome = self._plan_service.process_feedback_cycle(
                user_id, plan_id, note=saved.free_text, route=decision.route
            )
            if not outcome.reasons:
                outcome.reasons = [decision.reason]
            adjustment = outcome
            if outcome.new_plan_id is not None and self._replan_service is not None:
                eligibility = self._replan_service.check_eligibility(
                    user_id, outcome.new_plan_id
                )

        replan_reason = decision.reason
        if adjustment is not None and adjustment.reasons:
            replan_reason = adjustment.reasons[0]

        return FeedbackSubmitResult(
            feedback=saved,
            replan_triggered=bool(adjustment and adjustment.new_plan_id),
            replan_plan_id=adjustment.new_plan_id if adjustment else None,
            replan_eligibility=eligibility,
            adjustment=adjustment,
            replan_decision=decision.route,
            replan_reason=replan_reason,
        )

    def list_feedback(self, user_id: int, plan_id: int) -> list[Feedback]:
        plan = self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError("plan not found")
        if plan.user_id != user_id:
            raise PermissionDeniedError("plan belongs to another user")
        return self._feedback.list_by_plan(plan_id)

    def _decide_replan(
        self, user_id: int, feedback: Feedback
    ) -> FeedbackReplanDecision:
        """Gate the agent cycle with the feedback policy.

        Reads the observed duration bias. Level 2 state is refreshed separately;
        the policy itself is driven by the current check-in plus that observed
        bias, never by a second portrait engine.
        """
        try:
            from app.application.services.profile_service import ProfileService

            duration_bias = ProfileService(self._session).duration_bias(user_id)
        except Exception:  # noqa: BLE001 - the feedback row is the record of truth
            self._session.rollback()
            duration_bias = 0.0

        settings = get_settings()
        return decide_feedback_replan(
            stress=feedback.stress_level,
            energy=feedback.energy_level,
            completion_rate=feedback.completion_rate or 0.0,
            duration_bias=duration_bias,
            portrait_decision="none",
            stress_high=settings.agent_feedback_stress_high,
            energy_low=settings.agent_feedback_energy_low,
            stress_severe=settings.agent_feedback_stress_severe,
            energy_critical=settings.agent_feedback_energy_critical,
            duration_bias_high=settings.agent_feedback_duration_bias_high,
        )

    def _refresh_memory(self, user_id: int) -> None:
        """Update persisted memory; never let it break a feedback submission."""
        from app.application.services.memory_service import MemoryService

        service = MemoryService(self._session)
        try:
            service.refresh(user_id)
        except Exception:  # noqa: BLE001 - memory is best-effort, feedback is the record
            self._session.rollback()

    def _refresh_user_model(self, user_id: int) -> None:
        """Replay Level 2 from real history; best-effort only."""
        from app.application.services.user_model_service import UserModelService

        try:
            UserModelService(self._session).refresh_dynamic_state(user_id)
        except Exception:  # noqa: BLE001 - the feedback row is the record of truth
            self._session.rollback()
