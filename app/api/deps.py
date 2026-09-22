"""FastAPI dependencies: DB session, services and the current user."""

from __future__ import annotations

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
    ReplanService,
    SituationService,
    UserModelService,
)
from app.core.security import InvalidTokenError, decode_access_token
from app.domain.models import User
from app.infrastructure.database import SessionLocal

bearer_scheme = HTTPBearer(auto_error=False)

#: Process-wide registry of generation jobs (in-memory; see GenerationService).
_generation_service: GenerationService | None = None


def get_db() -> Iterator[Session]:
    """Yield a SQLAlchemy session; services own their commits."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_user_model_service(db: Session = Depends(get_db)) -> UserModelService:
    return UserModelService(db)


def get_plan_service(db: Session = Depends(get_db)) -> PlanService:
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
        _generation_service = GenerationService()
    return _generation_service


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
