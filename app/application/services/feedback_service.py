"""Feedback service: daily check-in submission and history."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.dto.feedback import FeedbackSubmitResult
from app.application.exceptions import NotFoundError, PermissionDeniedError
from app.domain.models import Feedback
from app.domain.models.enums import ReplanTriggerType
from app.infrastructure.database.repositories import (
    FeedbackRepository,
    PlanRepository,
    TaskRepository,
)

#: Below this daily completion rate a replan is auto-triggered (when eligible).
AUTO_REPLAN_THRESHOLD = 0.5


class FeedbackService:
    def __init__(self, session: Session, *, replan_service=None) -> None:
        self._session = session
        self._feedback = FeedbackRepository(session)
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)
        self._replan_service = replan_service

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

        triggered = False
        eligibility = None
        replan_plan_id: int | None = None
        if self._replan_service is not None:
            eligibility = self._replan_service.check_eligibility(user_id, plan_id)
            if saved.completion_rate < AUTO_REPLAN_THRESHOLD and eligibility.eligible:
                result = self._replan_service.replan(
                    user_id,
                    plan_id,
                    reason="auto replan: low daily completion rate",
                    trigger_type=ReplanTriggerType.FEEDBACK_TRIGGERED,
                )
                triggered = True
                replan_plan_id = result.plan.id
                eligibility = self._replan_service.check_eligibility(user_id, plan_id)

        return FeedbackSubmitResult(
            feedback=saved,
            replan_triggered=triggered,
            replan_plan_id=replan_plan_id,
            replan_eligibility=eligibility,
        )

    def list_feedback(self, user_id: int, plan_id: int) -> list[Feedback]:
        plan = self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError("plan not found")
        if plan.user_id != user_id:
            raise PermissionDeniedError("plan belongs to another user")
        return self._feedback.list_by_plan(plan_id)
