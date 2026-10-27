"""Feedback endpoints (daily check-in)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_current_user,
    get_execution_reconciliation_service,
    get_feedback_service,
    get_generation_service,
)
from app.application.services import (
    ExecutionReconciliationService,
    FeedbackService,
    GenerationService,
    PlanService,
)
from app.domain.models import Feedback, User
from app.schemas.common import ErrorResponse
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackObligationRead,
    FeedbackRead,
    FeedbackSubmitResponse,
)
from app.schemas.plan import FeedbackAdjustmentRead, ReplanEligibilityRead

router = APIRouter()
#: `/feedback/obligations` lives outside the `/plans` prefix on purpose: a path
#: under `/plans` would collide with `GET /plans/{plan_id}`.
obligations_router = APIRouter()

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
    feedback = Feedback(
        user_id=user_id,
        plan_id=plan_id,
        date=payload.date,
        completion_rate=payload.completion_rate,
        stress_level=payload.stress_level,
        energy_level=payload.energy_level,
        delay_reason=payload.delay_reason,
        task_reasons=[item.model_dump() for item in payload.task_reasons],
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
            # The service policy already decided whether the cycle should run.
            if result.replan_decision == "none":
                return {
                    "replan_triggered": False,
                    "replan_plan_id": None,
                    "replan_decision": "none",
                    "replan_reason": result.replan_reason,
                    "adjustment": None,
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


@obligations_router.get(
    "/obligations",
    response_model=list[FeedbackObligationRead],
    summary="List unresolved daily-feedback obligations",
    description=(
        "Backend-authoritative list of `user + execution_date` feedback debts. "
        "A day appears only when it already contains observed execution behaviour "
        "and no check-in was submitted. Older days stay pending across day "
        "boundaries (`is_retrospective=true`) instead of disappearing."
    ),
    responses={**_AUTH},
)
def list_feedback_obligations(
    current_user: User = Depends(get_current_user),
    reconciliation: ExecutionReconciliationService = Depends(
        get_execution_reconciliation_service
    ),
) -> list[FeedbackObligationRead]:
    user_id = current_user.id or 0
    # Settle past task/occurrence states on the same deterministic read, then
    # derive the outstanding debt from persisted behaviour.
    reconciliation.reconcile_user_execution_state(user_id)
    return [
        FeedbackObligationRead(
            execution_date=obligation.execution_date,
            status=obligation.status,
            is_retrospective=obligation.is_retrospective,
            plan_id=obligation.plan_id,
        )
        for obligation in reconciliation.list_feedback_obligations(user_id)
    ]
