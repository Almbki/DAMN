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

import logging
from datetime import UTC, datetime

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
    TaskExecutionRepository,
    TaskRepository,
)

logger = logging.getLogger(__name__)


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
        self._executions = TaskExecutionRepository(session)
        self._replan_service = replan_service
        self._plan_service = plan_service

    def submit_feedback(
        self,
        user_id: int,
        plan_id: int,
        feedback: Feedback,
        *,
        defer_replan: bool = False,
        close_day: bool = False,
        task_estimates: list[dict] | None = None,
    ) -> FeedbackSubmitResult:
        """Persist the check-in and (optionally) run the feedback cycle.

        ``defer_replan`` is used by the streaming API: the expensive agent cycle
        runs in a background job after this call returns, so only the check-in
        side effects happen here. ``close_day`` stamps ``day_closed_at`` and
        ``task_estimates`` patches the latest execution rows (best effort).
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
                # Closing the day is a user action: stamp the moment it happened.
                "day_closed_at": (
                    datetime.now(UTC) if close_day else feedback.day_closed_at
                ),
            }
        )
        saved = self._feedback.create(payload)
        self._session.commit()

        # Estimate corrections are best-effort: a missing execution row must
        # never block the check-in, which is the record of truth.
        self._apply_task_estimates(plan_id, task_estimates)

        # Consolidate what we just learned into persisted memory (semantic /
        # episodic / procedural), so the next planning run reads it back.
        self._refresh_memory(user_id)
        # ... and refresh the real Level 2 dynamic state from the new check-in.
        self._refresh_user_model(user_id)

        eligibility = None
        if self._replan_service is not None:
            eligibility = self._replan_service.check_eligibility(user_id, plan_id)

        decision = self._decide_replan(user_id, saved)
        route = decision.route
        replan_reason = decision.reason
        if (
            route == "full_replan"
            and eligibility is not None
            and not eligibility.eligible
        ):
            # A big rebuild has a cooldown (one per day at most by default). When
            # it is still cooling down, do the cheap content-preserving move
            # instead of churning another plan version.
            route = "postpone"
            replan_reason = (
                "full replan blocked by cooldown; postponed instead: "
                + decision.reason
            )
        adjustment = None
        postponed_task_ids: list[int] = []

        if self._plan_service is not None:
            if route == "postpone":
                # Cheap, deterministic and content-preserving: move today's
                # unfinished tasks to tomorrow; only escalate when that day is
                # already full.
                postponement = self._plan_service.postpone_unfinished(
                    user_id, plan_id, day=saved.date
                )
                postponed_task_ids = list(postponement.postponed_task_ids)
                if postponement.over_capacity:
                    route = "micro_adjust"
                    replan_reason = (
                        "postpone skipped: tomorrow would need "
                        f"{postponement.tomorrow_load_minutes} of "
                        f"{postponement.tomorrow_capacity_minutes} minutes; "
                        f"{decision.reason}"
                    )
                    if not defer_replan:
                        outcome = self._plan_service.process_feedback_cycle(
                            user_id,
                            plan_id,
                            note=saved.free_text,
                            route="micro_adjust",
                        )
                        if not outcome.reasons:
                            outcome.reasons = [replan_reason]
                        adjustment = outcome
                        if (
                            outcome.new_plan_id is not None
                            and self._replan_service is not None
                        ):
                            eligibility = self._replan_service.check_eligibility(
                                user_id, outcome.new_plan_id
                            )
            elif route != "none" and not defer_replan:
                # Free text is context for the prompt only: it no longer sets
                # `user_adjustment`, so it cannot force a FULL_REPLAN by itself.
                outcome = self._plan_service.process_feedback_cycle(
                    user_id, plan_id, note=saved.free_text, route=route
                )
                if not outcome.reasons:
                    outcome.reasons = [decision.reason]
                adjustment = outcome
                if outcome.new_plan_id is not None and self._replan_service is not None:
                    eligibility = self._replan_service.check_eligibility(
                        user_id, outcome.new_plan_id
                    )

        if adjustment is not None and adjustment.reasons:
            replan_reason = adjustment.reasons[0]

        return FeedbackSubmitResult(
            feedback=saved,
            replan_triggered=bool(adjustment and adjustment.new_plan_id),
            replan_plan_id=adjustment.new_plan_id if adjustment else None,
            replan_eligibility=eligibility,
            adjustment=adjustment,
            replan_decision=route,
            replan_reason=replan_reason,
            postponed_task_ids=postponed_task_ids,
        )

    def list_feedback(self, user_id: int, plan_id: int) -> list[Feedback]:
        plan = self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError("plan not found")
        if plan.user_id != user_id:
            raise PermissionDeniedError("plan belongs to another user")
        return self._feedback.list_by_plan(plan_id)

    def _apply_task_estimates(
        self, plan_id: int, estimates: list[dict] | None
    ) -> None:
        """Patch the latest execution row with the user's estimate feedback.

        Best effort by design: unknown tasks, tasks from another plan and tasks
        without an execution row are skipped, and any failure is rolled back so
        the already-saved check-in is never lost.
        """
        if not estimates:
            return
        try:
            for item in estimates:
                task_id = int(item.get("task_id") or 0)
                task = self._tasks.get_by_id(task_id)
                if task is None or task.plan_id != plan_id:
                    continue
                executions = self._executions.list_by_task(task_id)
                if not executions:
                    continue
                fields: dict[str, object] = {}
                accuracy = item.get("accuracy")
                if accuracy in {"over", "under", "ok"}:
                    fields["estimate_feedback"] = accuracy
                actual_minutes = item.get("actual_minutes")
                if actual_minutes is not None:
                    fields["actual_duration"] = int(actual_minutes)
                if fields:
                    self._executions.update_fields(
                        executions[-1].id or 0, **fields
                    )
            self._session.commit()
        except Exception:  # noqa: BLE001 - the check-in is the record of truth
            logger.warning(
                "task estimate feedback failed for plan=%s", plan_id, exc_info=True
            )
            self._session.rollback()

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
