"""Plan endpoints: generation (with SSE), listing, detail, replanning."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.agent.state import GenerationRequest, GoalInput, PreferenceInput
from app.api.deps import (
    get_current_user,
    get_generation_service,
    get_plan_service,
    get_replan_service,
)
from app.api.v1.mappers import (
    decompose_response,
    plan_change_read,
    plan_list_item,
    plan_read,
    preview_read,
)
from app.application.exceptions import (
    ConflictError,
    NotFoundError,
    ReplanNotEligibleError,
)
from app.application.services import GenerationService, PlanService, ReplanService
from app.core.config import get_settings
from app.domain.models import User
from app.domain.models.enums import GoalType, Priority
from app.domain.scheduling.constants import DEFAULT_HORIZON_DAYS
from app.schemas.common import ErrorResponse
from app.schemas.plan import (
    AdjustRequest,
    AdjustResponse,
    ClarificationQuestionRead,
    ClarificationRead,
    ConfirmDraftRequest,
    ConfirmResponse,
    DecomposeRequest,
    JobAcceptedResponse,
    JobStatusResponse,
    PlanChangeRead,
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanListItem,
    PlanRead,
    PreviewResponse,
    ReplanEligibilityRead,
    ReplanRequest,
    ReplanResponse,
)

#: Default scheduling horizon when the client does not send an end date.
router = APIRouter()

_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Plan not found"}}
_FORBIDDEN = {403: {"model": ErrorResponse, "description": "Not your plan"}}
_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}


def _to_generation_request(user: User, payload: PlanGenerateRequest) -> GenerationRequest:
    """Map the API payload onto the graph input.

    Only the caps the client actually sent go into ``preferences``; the rest
    falls back to the user's stored scheduling preferences inside the graph
    (`resolve_preferences`). ``user_profile`` is forwarded as ``profile``.
    """
    start = payload.start_date or date.today()
    end = payload.end_date or (start + timedelta(days=DEFAULT_HORIZON_DAYS))
    overrides = PreferenceInput(
        available_minutes_per_day=payload.available_minutes_per_day,
        daily_limit_minutes=payload.daily_limit_minutes,
        buffer_minutes=payload.buffer_minutes,
        high_cognitive_max_per_day=payload.high_cognitive_max_per_day,
    )
    has_overrides = any(
        value is not None
        for value in (
            payload.available_minutes_per_day,
            payload.daily_limit_minutes,
            payload.buffer_minutes,
            payload.high_cognitive_max_per_day,
        )
    )
    return GenerationRequest(
        user_id=user.id or 0,
        timezone=payload.timezone,
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
                start_date=goal.start_date,
                task_kind=goal.task_kind,
                planning_mode=goal.planning_mode,
                recurrence_frequency=goal.recurrence_frequency,
                recurrence_interval=goal.recurrence_interval,
                daily_target_minutes=goal.daily_target_minutes,
                recurrence_weekdays=goal.recurrence_weekdays,
                clarifications=dict(goal.clarifications or {}),
                target_amount=goal.target_amount,
                target_unit=goal.target_unit,
            )
            for goal in payload.goals
        ],
        start_date=start,
        end_date=end,
        plan_title=payload.plan_title,
        goal_set_id=payload.goal_set_id,
        goal_set_name=payload.goal_set_name,
        preferences=overrides if has_overrides else None,
        profile=dict(payload.user_profile or {}),
        execution_weight=(
            payload.execution_weight
            if payload.execution_weight is not None
            else user.execution_weight
        ),
    )


def _decompose_request(user: User, payload: DecomposeRequest) -> GenerationRequest:
    """Map the frontend's decompose payload onto the graph input.

    The four scheduling caps are omitted on purpose so the user's stored
    preferences apply (see `resolve_preferences`).
    """
    start = date.today()
    end = start + timedelta(days=DEFAULT_HORIZON_DAYS)
    return GenerationRequest(
        user_id=user.id or 0,
        timezone=payload.timezone,
        goals=[
            GoalInput(
                title=goal.title,
                description=goal.notes,
                deadline=(
                    datetime.combine(goal.deadline, time.min) if goal.deadline else None
                ),
                priority=Priority(goal.priority),
                goal_type=goal.goal_type or GoalType.SHORT_TERM,
                start_date=goal.start_date,
                task_kind=goal.task_kind,
                planning_mode=goal.planning_mode,
                recurrence_frequency=goal.recurrence_frequency,
                recurrence_interval=goal.recurrence_interval,
                daily_target_minutes=goal.daily_target_minutes,
                recurrence_weekdays=goal.recurrence_weekdays,
                clarifications=dict(goal.clarifications or {}),
                target_amount=goal.target_amount,
                target_unit=goal.target_unit,
            )
            for goal in payload.goals
        ],
        start_date=start,
        end_date=end,
        plan_title=None,
        goal_set_id=payload.goal_set_id,
        goal_set_name=payload.goal_set_name,
        preferences=None,
        profile={},
        execution_weight=user.execution_weight,
    )


def _job_status_value(job) -> str:
    """Normalise a job status (enum or plain str) to its string value."""
    status = getattr(job, "status", None)
    return str(getattr(status, "value", status) or "")


def _job_accepted(job) -> JobAcceptedResponse:
    """Build the 202 payload shared by the async generation routes."""
    settings = get_settings()
    return JobAcceptedResponse(
        job_id=job.job_id,
        status=_job_status_value(job),
        events_url=f"{settings.api_v1_prefix}/plans/generation/{job.job_id}/events",
        status_url=f"{settings.api_v1_prefix}/plans/generation/{job.job_id}",
    )


def preview_response_dict(result) -> dict:
    """JSON-able job result matching :class:`PreviewResponse`."""
    clarification = None
    if getattr(result, "clarification", None) is not None:
        clarification = ClarificationRead(
            status=result.clarification.status,
            questions=[
                ClarificationQuestionRead(
                    goal_id=q.goal_id,
                    field=q.field,
                    question=q.question,
                    required=q.required,
                )
                for q in result.clarification.questions
            ],
        )
    return PreviewResponse(
        thread_id=result.thread_id,
        preview=preview_read(result.preview) if result.preview is not None else None,
        clarification=clarification,
        plan_id=None,
        goals_persisted=result.goals_persisted,
        goal_set_id=result.goal_set_id,
        degraded=result.degraded,
        warnings=result.warnings,
    ).model_dump(mode="json")


def decompose_job_result(result) -> dict:
    """JSON-able decompose result, keeping the resumable preview alongside it.

    The contract shape stays ``DecomposeResponse`` (``draft_id`` + ``days``);
    ``thread_id``/``preview`` are additive so ``GET /plans/preview/latest`` can
    recover a decomposition on another device with the usual preview payload.
    """
    payload = decompose_response(result.thread_id, result.preview).model_dump(mode="json")
    payload["thread_id"] = result.thread_id
    payload["preview"] = preview_read(result.preview).model_dump(mode="json")
    return payload


def adjust_response_dict(result, thread_id: str, final_plan: PlanRead | None = None) -> dict:
    """JSON-able job result matching :class:`AdjustResponse`."""
    if result.preview is None:
        # Budget exhausted: the graph finalised the plan.
        return AdjustResponse(
            thread_id=thread_id,
            budget_exhausted=True,
            final_plan=final_plan,
            degraded=result.degraded,
            warnings=result.warnings,
        ).model_dump(mode="json")
    return AdjustResponse(
        thread_id=thread_id,
        preview=preview_read(result.preview),
        budget_exhausted=result.budget_exhausted,
        degraded=result.degraded,
        warnings=result.warnings,
    ).model_dump(mode="json")


@router.post(
    "/generate",
    response_model=PlanGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate a first plan from goals (async job)",
    description=(
        "Async job. Runs the LangGraph planning pipeline (goal analysis -> theoretical "
        "analysis -> user situation analysis -> plan generation -> rule validation -> "
        "plan repair) and persists a new plan version. Returns 202 with `events_url` "
        "(SSE stream) and `status_url` (poll); the job result carries `plan_id` and "
        "the persisted `plan`."
    ),
    responses={**_AUTH, 422: {"model": ErrorResponse, "description": "Invalid goals"}},
)
def generate_plan(
    payload: PlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> PlanGenerateResponse:
    user_id = current_user.id or 0
    # Build the graph input up-front: it must not depend on the request session
    # once the background worker (own session) takes over.
    request = _to_generation_request(current_user, payload)

    def runner(service: PlanService, emit) -> dict:
        detail, _events = service.generate_plan_with_events(user_id, request, emit=emit)
        return {
            "plan_id": detail.plan.id,
            "plan": plan_read(detail).model_dump(mode="json"),
        }

    job = generation_service.submit(user_id=user_id, kind="generate", runner=runner)
    settings = get_settings()
    return PlanGenerateResponse(
        job_id=job.job_id,
        status=_job_status_value(job),
        plan_id=None,
        events_url=f"{settings.api_v1_prefix}/plans/generation/{job.job_id}/events",
        status_url=f"{settings.api_v1_prefix}/plans/generation/{job.job_id}",
        plan=None,
    )


@router.post(
    "/preview",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate a plan preview and pause for confirmation (async job)",
    description=(
        "Async job. Runs the LangGraph preview pipeline (context -> goal analysis -> "
        "theoretical analysis -> user situation -> plan generation -> rule validation "
        "-> preview) and PAUSES. Apart from the goals, nothing is persisted yet. "
        "Returns 202 with `events_url` (SSE stream) and `status_url` (poll). The job "
        "result has the `PreviewResponse` shape; resume with "
        "`POST /plans/preview/{thread_id}/confirm` or `/adjust`."
    ),
    responses={**_AUTH, 422: {"model": ErrorResponse, "description": "Invalid goals"}},
)
def preview_plan(
    payload: PlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> JobAcceptedResponse:
    user_id = current_user.id or 0
    # Build the graph input up-front: it must not depend on the request session
    # once the background worker (own session) takes over.
    request = _to_generation_request(current_user, payload)

    def runner(service: PlanService, emit) -> dict:
        result = service.generate_preview(user_id, request, emit=emit)
        return preview_response_dict(result)

    job = generation_service.submit(user_id=user_id, kind="preview", runner=runner)
    return _job_accepted(job)


@router.get(
    "/preview/latest",
    response_model=PreviewResponse,
    summary="Recover the latest actionable preview (cross-device)",
    description=(
        "Returns the current user's newest completed preview-like job result "
        "that still carries a `thread_id` and `preview` payload. This lets a "
        "client on another device recover an unconfirmed preview after reload. "
        "404 when there is none. A returned preview may since have been confirmed "
        "or expired in the LangGraph checkpointer: in that case confirm still "
        "answers idempotently with the existing plan or 404 - the stored preview "
        "is a snapshot, not proof the draft is still resumable."
    ),
    responses={**_AUTH, **_NOT_FOUND},
)
def latest_preview(
    current_user: User = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> PreviewResponse:
    result = generation_service.latest_preview(current_user.id or 0)
    if result is None:
        raise NotFoundError("no actionable preview found")
    return PreviewResponse.model_validate(result)


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
    if result.pending_preview is not None or result.detail is None:  # pragma: no cover
        raise ConflictError("preview is still pending; adjust or confirm again")
    return ConfirmResponse(
        plan=plan_read(result.detail),
        degraded=result.degraded,
        warnings=result.warnings,
    )


@router.post(
    "/preview/{thread_id}/adjust",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a bounded preview adjustment (async job)",
    description=(
        "Async job. Applies ONE user change to the preview and pauses again. The "
        "budget is limited (AGENT_MAX_PREVIEW_ADJUSTMENTS); once exhausted the plan "
        "is finalised instead and the result's `budget_exhausted` is true - the user "
        "should start executing rather than keep regenerating. Returns 202 with "
        "`events_url` (SSE stream) and `status_url` (poll); the job result has the "
        "`AdjustResponse` shape."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def adjust_preview(
    thread_id: str,
    payload: AdjustRequest,
    current_user: User = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> JobAcceptedResponse:
    user_id = current_user.id or 0
    feedback = payload.feedback

    def runner(service: PlanService, emit) -> dict:
        result = service.adjust_preview(user_id, thread_id, feedback, emit=emit)
        detail = (
            service.get_plan(user_id, result.plan_id)
            if result.preview is None and result.plan_id is not None
            else None
        )
        return adjust_response_dict(
            result, thread_id=thread_id, final_plan=plan_read(detail) if detail else None
        )

    job = generation_service.submit(user_id=user_id, kind="preview_adjust", runner=runner)
    return _job_accepted(job)


@router.post(
    "/decompose",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Decompose several goals into a per-day draft (async job, not persisted)",
    description=(
        "Async job. Frontend contract: send the goals you want split up and the job "
        "produces a draft grouped by day. Nothing is persisted except the goals. "
        "Returns 202 with `events_url` (SSE stream) and `status_url` (poll); the job "
        "result has the `DecomposeResponse` shape. Pass `draft_id` + `feedback` to "
        "regenerate the same draft (bounded by `AGENT_MAX_PREVIEW_ADJUSTMENTS`; over "
        "budget still returns an immediate 409)."
    ),
    responses={
        **_AUTH,
        409: {"model": ErrorResponse, "description": "Adjustment budget exhausted"},
    },
)
def decompose_plan(
    payload: DecomposeRequest,
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
    generation_service: GenerationService = Depends(get_generation_service),
) -> JobAcceptedResponse:
    user_id = current_user.id or 0

    if payload.draft_id:
        # Regeneration path: validate immediately (404 / 403 / 409) before the
        # background job starts, so an exhausted budget is still an HTTP 409.
        pending = plan_service.pending_draft(user_id, payload.draft_id)
        used = int(pending.get("adjustment_count") or 0)
        limit = plan_service.max_preview_adjustments
        if used >= limit:
            raise ConflictError(
                f"调整次数已用完（{used}/{limit}），请先执行当前计划再重新拆解"
            )
        draft_id = payload.draft_id
        feedback = payload.feedback or ""

        def runner(service: PlanService, emit) -> dict:
            result = service.adjust_preview(user_id, draft_id, feedback, emit=emit)
            if result.preview is None:  # budget hit on this very call
                raise ConflictError("调整次数已用完，草稿已定稿为正式计划")
            return decompose_job_result(result)

        job = generation_service.submit(user_id=user_id, kind="decompose", runner=runner)
        return _job_accepted(job)

    request = _decompose_request(current_user, payload)

    def runner(service: PlanService, emit) -> dict:
        result = service.generate_preview(user_id, request, emit=emit)
        return decompose_job_result(result)

    job = generation_service.submit(user_id=user_id, kind="decompose", runner=runner)
    return _job_accepted(job)


@router.post(
    "/confirm",
    response_model=PlanRead,
    status_code=status.HTTP_200_OK,
    summary="Confirm a draft and persist it as a plan",
    description=(
        "Frontend contract: `{draft_id}`. Returns the full plan so the client does "
        "not need a follow-up fetch. 404 when the draft is unknown/expired, 409 "
        "when it was already confirmed."
    ),
    responses={
        **_AUTH,
        **_NOT_FOUND,
        409: {"model": ErrorResponse, "description": "Already confirmed"},
    },
)
def confirm_draft(
    payload: ConfirmDraftRequest,
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
) -> PlanRead:
    user_id = current_user.id or 0
    # confirm_plan is idempotent: a repeated confirm returns the same plan, and
    # a retry after a successful graph run + failed persist reuses its final state.
    result = plan_service.confirm_plan(user_id, payload.draft_id)
    if result.pending_preview is not None:  # pragma: no cover - confirm finalises
        raise ConflictError("draft is still pending")
    return plan_read(result.detail)


@router.get(
    "/generation/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll a generation job's status",
    description=(
        "Polling fallback for the async generation routes. Returns the job's "
        "`kind`, `status`, recorded `events` and, once completed, the job-specific "
        "`result` payload (a `PreviewResponse`/`AdjustResponse` shape) - or `error` "
        "when it failed. Prefer the `events_url` SSE stream for live progress."
    ),
    responses={**_AUTH, **_NOT_FOUND},
)
def generation_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> JobStatusResponse:
    payload = generation_service.get_status(job_id, current_user.id or 0)
    return JobStatusResponse.model_validate(payload)


@router.get(
    "/generation/{job_id}/events",
    summary="Stream plan generation progress (SSE)",
    description=(
        "Server-Sent Events stream for a generation job. Each frame is "
        "`event: <stage>` with a JSON body; stages are goal_analysis, "
        "theoretical_analysis, user_situation_analysis, plan_generation, "
        "rule_validation, plan_repair and finally completed."
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


@router.get(
    "/{plan_id}/changes",
    response_model=list[PlanChangeRead],
    summary="What the system changed, day by day",
    description=(
        "Replan history for this plan version, with a per-day diff (added / moved "
        "/ removed tasks and a short summary). The diff is derived by comparing "
        "the task rows of the previous version with this one."
    ),
    responses={**_AUTH, **_NOT_FOUND, **_FORBIDDEN},
)
def list_plan_changes(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    plan_service: PlanService = Depends(get_plan_service),
) -> list[PlanChangeRead]:
    changes = plan_service.list_changes(current_user.id or 0, plan_id)
    return [plan_change_read(change) for change in changes]


@router.post(
    "/{plan_id}/replan",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a replan (async job, creates a new plan version)",
    description=(
        "Async job. Creates plan v(n+1) instead of overwriting v(n), re-schedules "
        "the unfinished tasks and records a ReplanEvent. Subject to the cooldown: "
        "an ineligible plan still returns an immediate 409. Returns 202 with "
        "`events_url` (SSE stream) and `status_url` (poll); the job result has the "
        "`ReplanResponse` shape."
    ),
    responses={**_AUTH, **_NOT_FOUND, **_FORBIDDEN, 409: {"model": ErrorResponse}},
)
def replan(
    plan_id: int,
    payload: ReplanRequest,
    current_user: User = Depends(get_current_user),
    replan_service: ReplanService = Depends(get_replan_service),
    generation_service: GenerationService = Depends(get_generation_service),
) -> JobAcceptedResponse:
    user_id = current_user.id or 0
    # Cooldown is policy, checked before any agent work is done.
    eligibility = replan_service.check_eligibility(user_id, plan_id)
    if not eligibility.eligible:
        raise ReplanNotEligibleError(
            eligibility.reason, detail=eligibility.model_dump(mode="json")
        )

    reason = payload.reason or "user requested replan"
    trigger_type = payload.trigger_type

    def runner(service: PlanService, emit) -> dict:
        detail = service.replan_with_agent(user_id, plan_id, reason=reason, emit=emit)
        return ReplanResponse(
            plan_id=detail.plan.id or 0,
            old_version=(detail.plan.version - 1),
            new_version=detail.plan.version,
            changed_task_ids=service.latest_changed_task_ids(detail.plan.id or 0),
            reason=reason,
            trigger_type=trigger_type,
        ).model_dump(mode="json")

    job = generation_service.submit(user_id=user_id, kind="replan", runner=runner)
    return _job_accepted(job)


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
