"""API schemas package."""

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.common import ErrorResponse, HealthResponse, ViolationRead
from app.schemas.feedback import FeedbackCreate, FeedbackRead, FeedbackSubmitResponse
from app.schemas.plan import (
    DailyCompletionRead,
    GenerationEventRead,
    GoalCreate,
    GoalRead,
    InsightRead,
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanListItem,
    PlanRead,
    ReplanEligibilityRead,
    ReplanRequest,
    ReplanResponse,
)
from app.schemas.task import (
    TaskRead,
    TaskStandardRead,
    TaskStandardUpdate,
    TaskUpdateRequest,
)
from app.schemas.user import UserRead, UserUpdate

__all__ = [
    "DailyCompletionRead",
    "ErrorResponse",
    "FeedbackCreate",
    "FeedbackRead",
    "FeedbackSubmitResponse",
    "GenerationEventRead",
    "GoalCreate",
    "GoalRead",
    "HealthResponse",
    "InsightRead",
    "LoginRequest",
    "PlanGenerateRequest",
    "PlanGenerateResponse",
    "PlanListItem",
    "PlanRead",
    "RegisterRequest",
    "ReplanEligibilityRead",
    "ReplanRequest",
    "ReplanResponse",
    "TaskRead",
    "TaskStandardRead",
    "TaskStandardUpdate",
    "TaskUpdateRequest",
    "TokenResponse",
    "UserRead",
    "UserUpdate",
    "ViolationRead",
]
