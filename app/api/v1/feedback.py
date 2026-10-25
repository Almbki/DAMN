"""Feedback endpoints (daily check-in)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_current_user,
    get_feedback_service,
    get_generation_service,
)
from app.application.services import FeedbackService, GenerationService, PlanService
from app.domain.models import Feedback, User
from app.schemas.common import ErrorResponse
from app.schemas.feedback import FeedbackCreate, FeedbackRead, FeedbackSubmitResponse
from app.schemas.plan import FeedbackAdjustmentRead, ReplanEligibilityRead

router = APIRouter()

_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}
_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Plan not found"}}


def _adjustment_payload(outcome) -> dict | None:
    """JSON-able agent adjustment (route/severity/reasons/source/plan)."""
    if outcome is None:
        return None
    return FeedbackAdjustmentRead(
        route=outcome.route.value,
        severity=outcome.severity.value,
        reasons=outcome.reasons,
        source=outcome.source,
        new_plan_id=outcome.new_plan_id,
        degraded=outcome.degraded,
    ).model_dump(mode="json")


@router.post(
    "/{plan_id}/feedback",
    response_model=FeedbackSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit daily feedback for a plan",
    description=(
        "Stores the daily check-in (completion rate, stress, energy, reasons). "
        "The check-in is always persisted. A feedback policy based on current "
        "stress/energy plus the portrait (duration bias / recent completion) "
        "decides whether the plan is adjusted; completion rate or free text "
        "alone never triggers a replan. The response reports the policy route "
        "(`replan_decision`) and why (`replan_reason`)."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def submit_feedback(
    plan_id: int,
    payload: FeedbackCreate,
    stream_replan: bool = False,
    current_user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
    generation_service: GenerationService = Depends(get_generation_service),
) -> FeedbackSubmitResponse:
    user_id = current_user.id or 0
    # Full dump (not a hand-picked field list) so new check-in fields cannot be
    # silently dropped here.
    data = payload.model_dump()
    data["task_reasons"] = [item.model_dump() for item in payload.task_reasons]
    # These are actions on the check-in, not columns of the feedback row.
    close_day = bool(data.pop("close_day", False))
    task_estimates = data.pop("task_estimates", [])
    feedback = Feedback(user_id=user_id, plan_id=plan_id, **data)
    result = service.submit_feedback(
        user_id,
        plan_id,
        feedback,
        defer_replan=stream_replan,
        close_day=close_day,
        task_estimates=task_estimates,
    )

    replan_job_id: str | None = None
    if stream_replan:
        note = payload.free_text

        def runner(plan_service: PlanService, emit) -> dict:
            # The service policy already decided whether the cycle should run.
            if result.replan_decision in {"none", "postpone"}:
                # "postpone" already applied its (cheap) task move inside the
                # service; there is no agent cycle to run for it.
                return {
                    "replan_triggered": False,
                    "replan_plan_id": None,
                    "replan_decision": result.replan_decision,
                    "replan_reason": result.replan_reason,
                    "adjustment": None,
                    "postponed_task_ids": result.postponed_task_ids,
                }
            outcome = plan_service.process_feedback_cycle(
                user_id, plan_id, note=note, emit=emit
            )
            if not outcome.reasons:
                outcome.reasons = [result.replan_reason or "feedback cycle"]
            return {
                "replan_triggered": outcome.new_plan_id is not None,
                "replan_plan_id": outcome.new_plan_id,
                "replan_decision": result.replan_decision,
                "replan_reason": outcome.reasons[0] if outcome.reasons else None,
                "adjustment": _adjustment_payload(outcome),
                "postponed_task_ids": result.postponed_task_ids,
            }

        job = generation_service.submit(
            user_id=user_id, kind="feedback_replan", runner=runner
        )
        replan_job_id = job.job_id

    return FeedbackSubmitResponse(
        feedback=FeedbackRead.model_validate(result.feedback),
        replan_triggered=result.replan_triggered,
        replan_plan_id=result.replan_plan_id,
        replan_job_id=replan_job_id,
        replan_eligibility=(
            ReplanEligibilityRead.model_validate(result.replan_eligibility)
            if result.replan_eligibility
            else None
        ),
        adjustment=_adjustment_payload(result.adjustment),
        replan_decision=result.replan_decision,
        replan_reason=result.replan_reason,
        postponed_task_ids=result.postponed_task_ids,
    )


@router.get(
    "/{plan_id}/feedback",
    response_model=list[FeedbackRead],
    summary="List feedback history for a plan",
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def list_feedback(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
) -> list[FeedbackRead]:
    items = service.list_feedback(current_user.id or 0, plan_id)
    return [FeedbackRead.model_validate(item) for item in items]
