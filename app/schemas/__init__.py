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
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    ProfileUpsert,
    RegisterRequestWithProfile,
    UserProfileRead,
    UserStateRead,
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
    "ProfileResponse",
    "ProfileUpdateRequest",
    "ProfileUpsert",
    "RegisterRequestWithProfile",
    "RegisterRequest",
    "ReplanEligibilityRead",
    "ReplanRequest",
    "ReplanResponse",
    "TaskRead",
    "TaskStandardRead",
    "TaskStandardUpdate",
    "TaskUpdateRequest",
    "TokenResponse",
    "UserProfileRead",
    "UserRead",
    "UserStateRead",
    "UserUpdate",
    "ViolationRead",
]
