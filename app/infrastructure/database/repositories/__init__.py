"""Repository implementations for the infrastructure layer.

Repositories are session-bound (constructed with a :class:`sqlalchemy.orm.Session`)
and NEVER commit - the service layer owns the transaction.
"""

from app.infrastructure.database.repositories.agent_memory_repository import (
    AgentMemoryRepository,
)
from app.infrastructure.database.repositories.agent_run_repository import AgentRunRepository
from app.infrastructure.database.repositories.base import RepositoryBase
from app.infrastructure.database.repositories.execution_repository import TaskExecutionRepository
from app.infrastructure.database.repositories.feedback_repository import FeedbackRepository
from app.infrastructure.database.repositories.goal_repository import GoalRepository
from app.infrastructure.database.repositories.plan_repository import PlanRepository
from app.infrastructure.database.repositories.prediction_log_repository import (
    PredictionLogRepository,
)
from app.infrastructure.database.repositories.replan_event_repository import ReplanEventRepository
from app.infrastructure.database.repositories.task_repository import TaskRepository
from app.infrastructure.database.repositories.task_standard_repository import TaskStandardRepository
from app.infrastructure.database.repositories.user_model_repository import UserModelRepository
from app.infrastructure.database.repositories.user_repository import UserRepository

__all__ = [
    "AgentMemoryRepository",
    "AgentRunRepository",
    "FeedbackRepository",
    "GoalRepository",
    "PlanRepository",
    "PredictionLogRepository",
    "ReplanEventRepository",
    "RepositoryBase",
    "TaskExecutionRepository",
    "TaskRepository",
    "TaskStandardRepository",
    "UserModelRepository",
    "UserRepository",
]