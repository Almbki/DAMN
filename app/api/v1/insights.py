"""Insight endpoints (plan analytics)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_insight_service
from app.api.v1.mappers import insight_read
from app.application.services import InsightService
from app.domain.models import User
from app.schemas.common import ErrorResponse
from app.schemas.plan import InsightRead

router = APIRouter()

_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}
_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Plan not found"}}


@router.get(
    "/{plan_id}/insights",
    response_model=InsightRead,
    summary="Get data insights for a plan",
    description=(
        "Aggregates completion rate, planned vs actual minutes, stress/energy "
        "averages, cognitive-load breakdown and simple recommendations."
    ),
    responses={**_AUTH, **_NOT_FOUND, 403: {"model": ErrorResponse}},
)
def get_insights(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    service: InsightService = Depends(get_insight_service),
) -> InsightRead:
    report = service.get_insights(current_user.id or 0, plan_id)
    return insight_read(report)
