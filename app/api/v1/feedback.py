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


@router.post(
    "/{plan_id}/feedback",
    response_model=FeedbackSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit daily feedback for a plan",
    description=(
        "Stores the daily check-in (completion rate, stress, energy, reasons). "
        "If the completion rate is below the auto-replan threshold and the plan "
        "is eligible, a replan is triggered and reported in the response."
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
    feedback = Feedback(
        user_id=user_id,
        plan_id=plan_id,
        date=payload.date,
        completion_rate=payload.completion_rate,
        stress_level=payload.stress_level,
        energy_level=payload.energy_level,
        delay_reason=payload.delay_reason,
        free_text=payload.free_text,
        sleep_hours=payload.sleep_hours,
        dominant_time_of_day=payload.dominant_time_of_day,
    )
    result = service.submit_feedback(
        user_id, plan_id, feedback, defer_replan=stream_replan
    )

    replan_job_id: str | None = None
    if stream_replan:
        note = payload.free_text

        def runner(plan_service: PlanService, emit) -> dict:
            outcome = plan_service.process_feedback_cycle(
                user_id, plan_id, note=note, emit=emit
            )
            return {
                "replan_triggered": outcome.new_plan_id is not None,
                "replan_plan_id": outcome.new_plan_id,
            }

        job = generation_service.submit(
            user_id=user_id, kind="feedback_replan", runner=runner
        )
        replan_job_id = job.job_id

    adjustment = None
    if result.adjustment is not None:
        adjustment = FeedbackAdjustmentRead(
            route=result.adjustment.route.value,
            severity=result.adjustment.severity.value,
            reasons=result.adjustment.reasons,
            source=result.adjustment.source,
            new_plan_id=result.adjustment.new_plan_id,
            degraded=result.adjustment.degraded,
        )
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
        adjustment=adjustment,
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
