"""Repository implementations for the infrastructure layer.

Repositories are session-bound (constructed with a :class:`sqlalchemy.orm.Session`)
and NEVER commit - the service layer owns the transaction.
"""

from app.infrastructure.database.repositories.agent_memory_repository import (
    AgentMemoryRepository,
)
from app.infrastructure.database.repositories.agent_run_repository import AgentRunRepository
from app.infrastructure.database.repositories.base import RepositoryBase
from app.infrastructure.database.repositories.daily_state_repository import DailyStateRepository
from app.infrastructure.database.repositories.evidence_item_repository import (
    EvidenceItemRepository,
)
from app.infrastructure.database.repositories.execution_repository import TaskExecutionRepository
from app.infrastructure.database.repositories.feedback_repository import FeedbackRepository
from app.infrastructure.database.repositories.generation_job_repository import (
    GenerationJobRepository,
)
from app.infrastructure.database.repositories.goal_repository import GoalRepository
from app.infrastructure.database.repositories.plan_repository import PlanRepository
from app.infrastructure.database.repositories.prediction_log_repository import (
    PredictionLogRepository,
)
from app.infrastructure.database.repositories.prediction_outcome_repository import (
    PredictionOutcomeRepository,
)
from app.infrastructure.database.repositories.prediction_snapshot_repository import (
    PredictionSnapshotRepository,
)
from app.infrastructure.database.repositories.replan_event_repository import ReplanEventRepository
from app.infrastructure.database.repositories.schedule_event_repository import (
    ScheduleEventRepository,
)
from app.infrastructure.database.repositories.shadow_prediction_repository import (
    ShadowPredictionRepository,
)
from app.infrastructure.database.repositories.synthetic_repository import (
    SyntheticDataRepository,
)
from app.infrastructure.database.repositories.task_dependency_repository import (
    TaskDependencyRepository,
)
from app.infrastructure.database.repositories.task_event_repository import TaskEventRepository
from app.infrastructure.database.repositories.task_repository import TaskRepository
from app.infrastructure.database.repositories.task_standard_repository import TaskStandardRepository
from app.infrastructure.database.repositories.trait_assessment_repository import (
    TraitAssessmentRepository,
)
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.repositories.user_state_repository import UserStateRepository

__all__ = [
    "AgentMemoryRepository",
    "AgentRunRepository",
    "DailyStateRepository",
    "EvidenceItemRepository",
    "FeedbackRepository",
    "GenerationJobRepository",
    "GoalRepository",
    "PlanRepository",
    "PredictionLogRepository",
    "PredictionOutcomeRepository",
    "PredictionSnapshotRepository",
    "ReplanEventRepository",
    "RepositoryBase",
    "ScheduleEventRepository",
    "ShadowPredictionRepository",
    "SyntheticDataRepository",
    "TaskDependencyRepository",
    "TaskEventRepository",
    "TaskExecutionRepository",
    "TaskRepository",
    "TaskStandardRepository",
    "TraitAssessmentRepository",
    "UserRepository",
    "UserStateRepository",
]