"""User endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    get_auth_service,
    get_current_user,
    get_profile_service,
    get_situation_service,
    get_trait_assessment_service,
)
from app.application.dto.trait_assessment import (
    TraitAssessmentData,
    TraitReassessmentEligibilityData,
)
from app.application.exceptions import NotFoundError
from app.application.services import (
    AuthService,
    ProfileService,
    SituationService,
    TraitAssessmentService,
)
from app.domain.models import User
from app.schemas.common import ErrorResponse
from app.schemas.profile import ModelRuntimeRead, ProfileRead
from app.schemas.trait_assessment import TraitAssessmentAnswerRequest
from app.schemas.user import (
    SchedulingPreferences,
    SituationTrendRead,
    UserRead,
    UserUpdate,
)

router = APIRouter()

_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}

#: Fields handled by ProfileService (dedicated columns + state reset).
PORTRAIT_FIELDS = frozenset({"mbti_type", "mbti_dims", "identity"})


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the current user",
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get(
    "/me/situation/trends",
    response_model=SituationTrendRead,
    summary="Energy / stress / efficacy trend for the profile page",
    description=(
        "Daily points over the last `days` (2-90, default 14). Days without a "
        "check-in have `null` values. `samples`/`min_samples`/`sufficient` say "
        "whether the history is enough to trust the curve; `drivers` explains "
        "the reasoning in plain language."
    ),
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def read_situation_trends(
    days: int = Query(default=14, ge=2, le=90),
    current_user: User = Depends(get_current_user),
    service: SituationService = Depends(get_situation_service),
) -> SituationTrendRead:
    report = service.get_trends(current_user.id or 0, days=days)
    return SituationTrendRead(**report.model_dump())


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update the current user profile",
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
    profiles: ProfileService = Depends(get_profile_service),
) -> UserRead:
    user_id = current_user.id or 0
    updated = service.update_user(
        user_id,
        display_name=payload.display_name,
        execution_weight=payload.execution_weight,
        profile=payload.profile,
    )
    # Portrait fields are handled separately: they live on dedicated columns and
    # changing them re-initialises the adaptive state. Only fields the client
    # actually sent are touched (an explicit null clears one).
    provided = PORTRAIT_FIELDS & payload.model_fields_set
    if provided or "trait_profile" in payload.model_fields_set:
        profiles.upsert_profile(
            user_id,
            provided=set(provided),
            mbti_type=payload.mbti_type,
            mbti_dims=payload.mbti_dims,
            identity=payload.identity,
            trait_profile=payload.trait_profile,
        )
        updated = service.get_user(user_id)
    return UserRead.model_validate(updated)


@router.get(
    "/me/profile",
    response_model=ProfileRead,
    summary="Read the user portrait (static MBTI + adaptive state)",
    description=(
        "404 when the user has not set a portrait yet. `degraded` is true while "
        "`update_count < 3`: the numbers are then cold-start priors derived from "
        "the MBTI template, not a psychological assessment."
    ),
    responses={**_AUTH, 404: {"model": ErrorResponse, "description": "Profile not set"}},
)
def read_profile(
    current_user: User = Depends(get_current_user),
    profiles: ProfileService = Depends(get_profile_service),
) -> ProfileRead:
    user_id = current_user.id or 0
    if not profiles.is_configured(user_id):
        raise NotFoundError("profile not set")
    snapshot = profiles.snapshot(user_id)
    return ProfileRead.from_parts(
        profiles.get_profile(user_id),
        profiles.get_state(user_id),
        trait=snapshot.get("level1"),
        level2=snapshot.get("level2"),
        model_metadata=snapshot.get("model_metadata") or [],
    )


@router.get(
    "/me/model-runtime",
    response_model=ModelRuntimeRead,
    summary="Inspect the three-layer user model runtime",
    description=(
        "Development/debug view: configured vs effective Level 3 mode, artifact "
        "versions/hashes for Level 1/2/3, and an aggregate shadow summary. "
        "Shadow predictions are never production inputs."
    ),
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def read_model_runtime(
    current_user: User = Depends(get_current_user),
    profiles: ProfileService = Depends(get_profile_service),
) -> ModelRuntimeRead:
    user_id = current_user.id or 0
    described = profiles.model_runtime_description()
    return ModelRuntimeRead(
        requested_mode=described["requested_mode"],
        effective_mode=described["effective_mode"],
        mode_reason=described.get("mode_reason"),
        layers=list(described.get("layers") or []),
        shadow_summary=profiles.shadow_summary(user_id),
    )


@router.post(
    "/me/trait-assessment/start",
    response_model=TraitAssessmentData,
    summary="Start or resume the Level 1 CAT assessment",
    description=(
        "Idempotent: returns the active assessment if one exists, or the latest "
        "completed assessment. Pass `?restart=true` to abandon an active session "
        "and start a new one. All item selection and stopping are performed by "
        "the backend Level 1 runtime."
    ),
    responses={**_AUTH, 503: {"model": ErrorResponse, "description": "Model unavailable"}},
)
def start_trait_assessment(
    restart: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    service: TraitAssessmentService = Depends(get_trait_assessment_service),
) -> TraitAssessmentData:
    return service.start(current_user.id or 0, restart=restart)


@router.get(
    "/me/trait-assessment/reassessment-eligibility",
    response_model=TraitReassessmentEligibilityData,
    summary="Check whether Level 1 can be reassessed now",
    description=(
        "Backend-authoritative cooldown. `eligible=false` includes the next "
        "eligible timestamp; the profile UI must not rely on local timers."
    ),
    responses={**_AUTH},
)
def trait_reassessment_eligibility(
    current_user: User = Depends(get_current_user),
    service: TraitAssessmentService = Depends(get_trait_assessment_service),
) -> TraitReassessmentEligibilityData:
    return service.reassessment_eligibility(current_user.id or 0)


@router.get(
    "/me/trait-assessment/{assessment_id}",
    response_model=TraitAssessmentData,
    summary="Resume a Level 1 CAT assessment",
    responses={**_AUTH, 404: {"model": ErrorResponse, "description": "Assessment not found"}},
)
def get_trait_assessment(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    service: TraitAssessmentService = Depends(get_trait_assessment_service),
) -> TraitAssessmentData:
    return service.get(current_user.id or 0, assessment_id)


@router.post(
    "/me/trait-assessment/{assessment_id}/answer",
    response_model=TraitAssessmentData,
    summary="Submit one CAT item response",
    responses={
        **_AUTH,
        404: {"model": ErrorResponse, "description": "Assessment not found"},
        409: {"model": ErrorResponse, "description": "Assessment completed or stale item"},
        422: {"model": ErrorResponse, "description": "Invalid item/response"},
        503: {"model": ErrorResponse, "description": "Model unavailable"},
    },
)
def answer_trait_assessment(
    assessment_id: str,
    payload: TraitAssessmentAnswerRequest,
    current_user: User = Depends(get_current_user),
    service: TraitAssessmentService = Depends(get_trait_assessment_service),
) -> TraitAssessmentData:
    return service.answer(
        current_user.id or 0,
        assessment_id,
        item_id=payload.item_id,
        response=payload.response,
    )


@router.get(
    "/me/preferences",
    response_model=SchedulingPreferences,
    summary="Read the scheduling preferences in effect",
    description=(
        "Effective values: the dedicated preferences column, falling back to "
        "legacy `profile` keys, then defaults. This is what plan generation uses "
        "when the request omits the four caps."
    ),
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def read_preferences(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> SchedulingPreferences:
    return SchedulingPreferences.model_validate(
        service.get_preferences(current_user.id or 0)
    )


@router.put(
    "/me/preferences",
    response_model=SchedulingPreferences,
    summary="Replace the scheduling preferences",
    description=(
        "Full overwrite (the frontend merges before submitting). Stored on a "
        "dedicated column so `PATCH /users/me` (wholesale `profile`) cannot wipe "
        "them. `POST /plans/generate` falls back to these when a cap is omitted."
    ),
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
def update_preferences(
    payload: SchedulingPreferences,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> SchedulingPreferences:
    updated = service.update_preferences(
        current_user.id or 0, payload.model_dump(mode="json")
    )
    return SchedulingPreferences.model_validate(updated)
