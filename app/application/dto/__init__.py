"""Application DTOs (return types of services).

These are internal application contracts - the API layer maps them to its own
response schemas so ORM/domain objects are never exposed directly.
"""

from app.application.dto.agent import (
    AdjustPreviewResult,
    ConfirmResult,
    FeedbackCycleOutcome,
    PreviewResult,
)
from app.application.dto.feedback import FeedbackSubmitResult
from app.application.dto.generation import AgentEvent, GenerationJob, JobStatus
from app.application.dto.insight import InsightReport
from app.application.dto.plan import PlanDetail, TaskWithStandards
from app.application.dto.replan import ReplanEligibility

__all__ = [
    "AdjustPreviewResult",
    "AgentEvent",
    "ConfirmResult",
    "FeedbackCycleOutcome",
    "FeedbackSubmitResult",
    "GenerationJob",
    "InsightReport",
    "JobStatus",
    "PlanDetail",
    "PreviewResult",
    "ReplanEligibility",
    "TaskWithStandards",
]
