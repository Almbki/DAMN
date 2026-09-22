"""FastAPI dependencies: DB session, services and the current user."""

from __future__ import annotations

import threading
from collections.abc import Iterator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.exceptions import AuthenticationError
from app.application.services import (
    AuthService,
    FeedbackService,
    GenerationService,
    GoalService,
    InsightService,
    PlanService,
    ProfileService,
    ReplanService,
    SituationService,
)
from app.core.security import InvalidTokenError, decode_access_token
from app.domain.models import User
from app.infrastructure.database import SessionLocal

bearer_scheme = HTTPBearer(auto_error=False)

#: Process-wide registry of generation jobs (in-memory; see GenerationService).
_generation_service: GenerationService | None = None
_generation_service_lock = threading.Lock()


def get_db() -> Iterator[Session]:
    """Yield a SQLAlchemy session; services own their commits."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_profile_service(db: Session = Depends(get_db)) -> ProfileService:
    return ProfileService(db)


def _build_plan_service(db: Session) -> PlanService:
    """Construct a fully-wired ``PlanService`` for ``db``.

    Shared by :func:`get_plan_service` (request session) and
    :func:`_plan_service_factory` (fresh session on a worker thread).
    """
    from app.agent.checkpointer import get_checkpointer
    from app.agent.llm import StructuredLLM
    from app.core.config import get_settings
    from app.infrastructure.llm.client import get_llm_client

    settings = get_settings()
    llm = StructuredLLM(
        get_llm_client(settings),
        max_retries=settings.agent_llm_max_retries,
        prompt_version=settings.agent_prompt_version,
    )
    return PlanService(db, llm=llm, checkpointer=get_checkpointer(settings))


def get_plan_service(db: Session = Depends(get_db)) -> PlanService:
    return _build_plan_service(db)


def _plan_service_factory() -> PlanService:
    """Build a ``PlanService`` on a fresh session (background worker)."""
    return _build_plan_service(SessionLocal())


def get_replan_service(db: Session = Depends(get_db)) -> ReplanService:
    return ReplanService(db)


def get_feedback_service(
    db: Session = Depends(get_db),
    replan_service: ReplanService = Depends(get_replan_service),
    plan_service: PlanService = Depends(get_plan_service),
) -> FeedbackService:
    return FeedbackService(db, replan_service=replan_service, plan_service=plan_service)


def get_insight_service(db: Session = Depends(get_db)) -> InsightService:
    return InsightService(db)


def get_goal_service(db: Session = Depends(get_db)) -> GoalService:
    return GoalService(db)


def get_situation_service(db: Session = Depends(get_db)) -> SituationService:
    return SituationService(db)


def get_generation_service() -> GenerationService:
    global _generation_service
    if _generation_service is None:
        with _generation_service_lock:
            if _generation_service is None:
                _generation_service = GenerationService(service_factory=_plan_service_factory)
    return _generation_service


def close_generation_service() -> None:
    """Shut down the process-wide generation service (workers + channels)."""
    global _generation_service
    with _generation_service_lock:
        service = _generation_service
        _generation_service = None
    if service is not None:
        service.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Resolve the authenticated user from a Bearer JWT."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise AuthenticationError("invalid or expired token") from exc
    return auth_service.get_user(int(payload.sub))
