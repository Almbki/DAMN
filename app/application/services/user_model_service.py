"""User model service: derive the statistical UserModel from real history.

First version uses :class:`StatisticalUserModelBuilder` (simple statistics -
NOT a trained ML model). The service contract is stable so a real model can be
plugged in later without changing the API.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.models import TaskExecution, UserModel
from app.domain.models.enums import CognitiveLoad
from app.infrastructure.database.repositories import (
    FeedbackRepository,
    TaskExecutionRepository,
    TaskRepository,
    UserModelRepository,
    UserRepository,
)
from app.ml.base import UserFeatureSet
from app.ml.user_model import StatisticalUserModelBuilder


class UserModelService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._models = UserModelRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._feedback = FeedbackRepository(session)
        self._tasks = TaskRepository(session)
        self._users = UserRepository(session)
        self._builder = StatisticalUserModelBuilder()

    def get_model(self, user_id: int) -> UserModel | None:
        return self._models.get_by_user(user_id)

    def update_model(self, user_id: int) -> UserModel:
        """Recompute and persist the user model from the latest history."""
        executions = self._executions.list_by_user(user_id)
        feedback = self._feedback.list_by_user(user_id)
        task_loads = self._task_loads(executions)
        model = self._builder.build(
            executions,
            feedback,
            user_id=user_id,
            task_loads=task_loads,
        )
        saved = self._models.upsert(model)
        self._session.commit()
        return saved

    def get_user_features(self, user_id: int) -> UserFeatureSet:
        """Build the feature set consumed by the predictors (read-only)."""
        executions = self._executions.list_by_user(user_id)
        feedback = self._feedback.list_by_user(user_id)
        model = self._models.get_by_user(user_id)
        user = self._users.get_by_id(user_id)
        execution_weight = user.execution_weight if user else 0.5
        features = self._builder.to_features(
            model,
            executions,
            feedback,
            user_id=user_id,
            execution_weight=execution_weight,
        )
        return features

    def _task_loads(self, executions: list[TaskExecution]) -> dict[int, CognitiveLoad]:
        loads: dict[int, CognitiveLoad] = {}
        for execution in executions:
            task = self._tasks.get_by_id(execution.task_id)
            if task is not None:
                loads[task.id] = task.cognitive_load  # type: ignore[index]
        return loads
