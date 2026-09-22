"""Plan endpoints: generation (with SSE), listing, detail, replanning."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.agent.state import GenerationRequest, GoalInput
from app.api.deps import (
    get_current_user,
    get_generation_service,
    get_plan_service,
    get_replan_service,
)
from app.api.v1.mappers import plan_list_item, plan_read, preview_read
from app.application.exceptions import ConflictError, ReplanNotEligibleError
from app.application.services import GenerationService, PlanService, ReplanService
from app.core.config import get_settings
from app.domain.models import User
from app.schemas.common import ErrorResponse
from app.schemas.plan import (
    AdjustRequest,
    AdjustResponse,
    ConfirmResponse,
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanListItem,
    PlanRead,
    PreviewResponse,
    ReplanEligibilityRead,
    ReplanRequest,
    ReplanResponse,
)

router = APIRouter()

_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Plan not found"}}
_FORBIDDEN = {403: {"model": ErrorResponse, "description": "Not your plan"}}
_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}


def _to_generation_request(user: User, payload: PlanGenerateRequest) -> GenerationRequest:
    start = payload.start_date or date.today()
    end = payload.end_date or (start + timedelta(days=13))
    return GenerationRequest(
        user_id=user.id or 0,
        goals=[
            GoalInput(
                title=goal.title,
                description=goal.description,
                goal_type=goal.goal_type,
                deadline=goal.deadline,
                priority=goal.priority,
                estimated_minutes=goal.estimated_minutes,
                subject=goal.subject,
                task_type=goal.task_type,
            )
            for goal in payload.goals
        ],
        start_date=start,
        end_date=end,
        plan_title=payload.plan_title,
        available_minutes_per_day=payload.available_minutes_per_day,
        daily_limit_minutes=payload.daily_limit_minutes,
        buffer_minutes=payload.buffer_minutes,
        high_cognitive_max_per_day=payload.high_cognitive_max_per_day,
        user_profile=payload.user_profile,
        execution_weight=(
            payload.execution_weight
            if payload.execution_weight is not None
            else user.execution_weight
        ),
    )


@router.post(
    "/generate",
    response_model=PlanGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate a first plan from goals",
    description=(
        "Runs the LangGraph planning pipeline (goal analysis -> theoretical analysis -> "
        "user situation analysis -> plan generation -> rule validation -> plan repair), "
        "persists a new plan version and returns a generation job id. "
        "Subscribe to the SSE endpoint for the stage-by-stage progress."
    ),
    responses={**_AUTH, 422: {"model": ErrorResponse, "description": "Invalid goals"}},
)
def generate_plan(
    payload: PlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
    generation_service: GenerationService = Depends(get_generation_service),
) -> PlanGenerateResponse:
    request = _to_generation_request(current_user, payload)
    job = generation_service.create_job(plan_service, current_user.id or 0, request)
    detail = (
        plan_service.get_plan(current_user.id or 0, job.plan_id)
        if job.plan_id is not None
        else None
    )
    settings = get_settings()
    return PlanGenerateResponse(
        job_id=job.job_id,
        status=job.status.value,
        plan_id=job.plan_id,
        events_url=f"{settings.api_v1_prefix}/plans/generation/{job.job_id}/events",
        plan=plan_read(detail) if detail else None,
    )


@router.post(
    "/preview",
    response_model=PreviewResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate a plan preview and pause for confirmation",
    description=(
        "Runs the LangGraph preview pipeline (context -> goal analysis -> theoretical "
        "analysis -> user situation -> plan generation -> rule validation -> preview) "
        "and PAUSES. Apart from the goals, nothing is persisted yet. Resume with "
        "`POST /plans/preview/{thread_id}/confirm` or `/adjust`."
    ),
    responses={**_AUTH, 422: {"model": ErrorResponse, "description": "Invalid goals"}},
)
def preview_plan(
    payload: PlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
) -> PreviewResponse:
    request = _to_generation_request(current_user, payload)
    result = plan_service.generate_preview(current_user.id or 0, request)
    return PreviewResponse(
        thread_id=result.thread_id,
        preview=preview_read(result.preview),
        plan_id=None,
        goals_persisted=result.goals_persisted,
        degraded=result.degraded,
        warnings=result.warnings,
    )


@router.post(
    "/preview/{thread_id}/confirm",
    response_model=ConfirmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm the preview and create the first plan version",
    description="Resumes the paused graph and persists plan v1.",
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def confirm_preview(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
) -> ConfirmResponse:
    result = plan_service.confirm_plan(current_user.id or 0, thread_id)
    if result.pending_preview is not None:  # pragma: no cover - confirm finalises
        raise ConflictError("preview is still pending; adjust or confirm again")
    return ConfirmResponse(
        plan=plan_read(result.detail),
        degraded=result.degraded,
        warnings=result.warnings,
    )


@router.post(
    "/preview/{thread_id}/adjust",
    response_model=AdjustResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a bounded preview adjustment",
    description=(
        "Applies ONE user change to the preview and pauses again. The budget is "
        "limited (AGENT_MAX_PREVIEW_ADJUSTMENTS); once exhausted the plan is "
        "finalised instead and `budget_exhausted` is true - the user should start "
        "executing rather than keep regenerating."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def adjust_preview(
    thread_id: str,
    payload: AdjustRequest,
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
) -> AdjustResponse:
    result = plan_service.adjust_preview(
        current_user.id or 0, thread_id, payload.feedback
    )
    if result.preview is None:
        # Budget exhausted: the graph finalised the plan.
        detail = (
            plan_service.get_plan(current_user.id or 0, result.plan_id)
            if result.plan_id is not None
            else None
        )
        return AdjustResponse(
            thread_id=thread_id,
            budget_exhausted=True,
            final_plan=plan_read(detail) if detail else None,
            degraded=result.degraded,
            warnings=result.warnings,
        )
    return AdjustResponse(
        thread_id=thread_id,
        preview=preview_read(result.preview),
        budget_exhausted=result.budget_exhausted,
        degraded=result.degraded,
        warnings=result.warnings,
    )


@router.get(
    "/generation/{job_id}/events",
    summary="Stream plan generation progress (SSE)",
    description=(
        "Server-Sent Events stream. Each frame is `event: <stage>` with a JSON body; "
        "stages are goal_analysis, theoretical_analysis, user_situation_analysis, "
        "plan_generation, rule_validation, plan_repair and finally completed."
    ),
    responses={**_AUTH, **_NOT_FOUND},
)
def generation_events(
    job_id: str,
    current_user: User = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> StreamingResponse:
    # Validate ownership before the response starts streaming.
    generation_service.get_job(job_id, current_user.id or 0)
    return StreamingResponse(
        generation_service.stream_sse(job_id, current_user.id or 0),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "",
    response_model=list[PlanListItem],
    summary="List the current user's plans",
    responses={**_AUTH},
)
def list_plans(
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
) -> list[PlanListItem]:
    plans = plan_service.list_plans(current_user.id or 0)
    items: list[PlanListItem] = []
    for plan in plans:
        task_count = 0
        completed_count = 0
        if plan.id is not None:
            try:
                detail = plan_service.get_plan(current_user.id or 0, plan.id)
            except Exception:  # pragma: no cover - defensive
                detail = None
            if detail is not None:
                task_count = len(detail.tasks)
                completed_count = sum(
                    1 for item in detail.tasks if item.task.status.value == "completed"
                )
        items.append(plan_list_item(plan, task_count=task_count, completed_count=completed_count))
    return items


@router.get(
    "/{plan_id}",
    response_model=PlanRead,
    summary="Get a plan with its tasks and standards",
    responses={**_AUTH, **_NOT_FOUND, **_FORBIDDEN},
)
def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
) -> PlanRead:
    detail = plan_service.get_plan(current_user.id or 0, plan_id)
    return plan_read(detail)


@router.post(
    "/{plan_id}/replan",
    response_model=ReplanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a replan (creates a new plan version)",
    description=(
        "Creates plan v(n+1) instead of overwriting v(n), re-schedules the "
        "unfinished tasks and records a ReplanEvent. Subject to the cooldown."
    ),
    responses={**_AUTH, **_NOT_FOUND, **_FORBIDDEN, 409: {"model": ErrorResponse}},
)
def replan(
    plan_id: int,
    payload: ReplanRequest,
    current_user: User = Depends(get_current_user),
    replan_service: ReplanService = Depends(get_replan_service),
    plan_service: PlanService = Depends(get_plan_service),
) -> ReplanResponse:
    user_id = current_user.id or 0
    # Cooldown is policy, checked before any agent work is done.
    eligibility = replan_service.check_eligibility(user_id, plan_id)
    if not eligibility.eligible:
        raise ReplanNotEligibleError(
            eligibility.reason, detail=eligibility.model_dump(mode="json")
        )

    detail = plan_service.replan_with_agent(
        user_id, plan_id, reason=payload.reason or "user requested replan"
    )
    return ReplanResponse(
        plan_id=detail.plan.id or 0,
        old_version=(detail.plan.version - 1),
        new_version=detail.plan.version,
        changed_task_ids=[item.task.id or 0 for item in detail.tasks],
        reason=payload.reason or "user requested replan",
        trigger_type=payload.trigger_type,
    )


@router.get(
    "/{plan_id}/replan/eligibility",
    response_model=ReplanEligibilityRead,
    summary="Check whether the plan can be replanned now",
    responses={**_AUTH, **_NOT_FOUND, **_FORBIDDEN},
)
def replan_eligibility(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    replan_service: ReplanService = Depends(get_replan_service),
) -> ReplanEligibilityRead:
    return ReplanEligibilityRead.model_validate(
        replan_service.check_eligibility(current_user.id or 0, plan_id)
    )
