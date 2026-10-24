"""Developer-only endpoints (feature-flagged).

Every endpoint is authenticated and always targets ``current_user.id``. The
request body cannot choose another user id.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_synthetic_scenario_service
from app.application.dto.synthetic import (
    SyntheticImportRequest,
    SyntheticImportSummary,
    SyntheticResetSummary,
    SyntheticScenarioList,
    SyntheticStatus,
)
from app.application.services import SyntheticScenarioService
from app.domain.models import User
from app.schemas.common import ErrorResponse

router = APIRouter()

_AUTH = {401: {"model": ErrorResponse, "description": "Not authenticated"}}
_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Feature disabled / not found"}}


@router.get(
    "/scenarios",
    response_model=SyntheticScenarioList,
    summary="List demo synthetic scenarios",
    responses={**_AUTH, **_NOT_FOUND},
)
def list_synthetic_scenarios(
    current_user: User = Depends(get_current_user),
    service: SyntheticScenarioService = Depends(get_synthetic_scenario_service),
) -> SyntheticScenarioList:
    return SyntheticScenarioList(scenarios=service.list_scenarios())


@router.get(
    "/scenarios/status",
    response_model=SyntheticStatus,
    summary="Synthetic data status for the current user",
    responses={**_AUTH, **_NOT_FOUND},
)
def synthetic_status(
    current_user: User = Depends(get_current_user),
    service: SyntheticScenarioService = Depends(get_synthetic_scenario_service),
) -> SyntheticStatus:
    return service.status(current_user.id or 0)


@router.post(
    "/scenarios/import",
    response_model=SyntheticImportSummary,
    summary="Import one synthetic scenario into the current user",
    description=(
        "Imports observations only. Level 2 and Level 3 are recomputed by the "
        "real runtime; model outputs cannot be supplied. The current JWT user "
        "is always the target."
    ),
    responses={**_AUTH, **_NOT_FOUND, 422: {"model": ErrorResponse}},
)
def import_synthetic_scenario(
    payload: SyntheticImportRequest,
    current_user: User = Depends(get_current_user),
    service: SyntheticScenarioService = Depends(get_synthetic_scenario_service),
) -> SyntheticImportSummary:
    return service.import_scenario(
        current_user.id or 0,
        scenario_name=payload.scenario_name,
        scenario=payload.scenario,
    )


@router.post(
    "/scenarios/reset",
    response_model=SyntheticResetSummary,
    summary="Delete only this user's synthetic data",
    responses={**_AUTH, **_NOT_FOUND},
)
def reset_synthetic_scenario(
    current_user: User = Depends(get_current_user),
    service: SyntheticScenarioService = Depends(get_synthetic_scenario_service),
) -> SyntheticResetSummary:
    return service.reset(current_user.id or 0)