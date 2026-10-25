"""Synthetic-data bookkeeping: counts, real/synthetic detection and reset.

Deletes are intentionally scoped to ``data_origin='synthetic'`` AND the current
user. Real observations and other users are never touched.
"""

from __future__ import annotations

from sqlalchemy import delete, func, or_, select

from app.infrastructure.database.models.daily_state import DailyState
from app.infrastructure.database.models.evidence_item import EvidenceItem
from app.infrastructure.database.models.execution import TaskExecution
from app.infrastructure.database.models.feedback import Feedback
from app.infrastructure.database.models.plan import Plan
from app.infrastructure.database.models.prediction_log import PredictionLog
from app.infrastructure.database.models.prediction_outcome import PredictionOutcome
from app.infrastructure.database.models.prediction_snapshot import PredictionSnapshot
from app.infrastructure.database.models.replan_event import ReplanEvent
from app.infrastructure.database.models.shadow_prediction import ShadowPrediction
from app.infrastructure.database.models.task import Task
from app.infrastructure.database.models.task_dependency import TaskDependency
from app.infrastructure.database.models.task_event import TaskEvent
from app.infrastructure.database.models.task_standard import TaskStandard
from app.infrastructure.database.models.trait_assessment import TraitAssessmentModel
from app.infrastructure.database.repositories.base import RepositoryBase

SYNTHETIC = "synthetic"


class SyntheticDataRepository(RepositoryBase):
    @staticmethod
    def _plan_ids(user_id: int):
        return select(Plan.id).where(Plan.user_id == user_id, Plan.data_origin == SYNTHETIC)

    @staticmethod
    def _task_ids(user_id: int):
        return select(Task.id).where(Task.plan_id.in_(SyntheticDataRepository._plan_ids(user_id)))

    def _count(self, stmt) -> int:
        return int(self._session.scalar(stmt) or 0)

    def counts(self, user_id: int) -> dict[str, int]:
        plan_ids = self._plan_ids(user_id)
        task_ids = self._task_ids(user_id)
        feedback_ids = select(Feedback.id).where(
            Feedback.user_id == user_id, Feedback.data_origin == SYNTHETIC
        )
        return {
            "plans": self._count(
                select(func.count()).select_from(Plan).where(
                    Plan.user_id == user_id, Plan.data_origin == SYNTHETIC
                )
            ),
            "tasks": self._count(
                select(func.count()).select_from(Task).where(Task.id.in_(task_ids))
            ),
            "task_executions": self._count(
                select(func.count()).select_from(TaskExecution).where(
                    TaskExecution.user_id == user_id,
                    TaskExecution.data_origin == SYNTHETIC,
                )
            ),
            "feedbacks": self._count(
                select(func.count()).select_from(Feedback).where(
                    Feedback.user_id == user_id, Feedback.data_origin == SYNTHETIC
                )
            ),
            "prediction_logs": self._count(
                select(func.count()).select_from(PredictionLog).where(
                    PredictionLog.user_id == user_id,
                    PredictionLog.data_origin == SYNTHETIC,
                )
            ),
            "shadow_predictions": self._count(
                select(func.count()).select_from(ShadowPrediction).where(
                    ShadowPrediction.user_id == user_id,
                    ShadowPrediction.data_origin == SYNTHETIC,
                )
            ),
            "trait_assessments": self._count(
                select(func.count()).select_from(TraitAssessmentModel).where(
                    TraitAssessmentModel.user_id == user_id,
                    TraitAssessmentModel.data_origin == SYNTHETIC,
                )
            ),
            "replan_events": self._count(
                select(func.count()).select_from(ReplanEvent).where(
                    ReplanEvent.plan_id.in_(plan_ids)
                )
            ),
            # --- Phase 1 record layer (so /dev/scenarios/status sees leftovers) ---
            "task_events": self._count(
                select(func.count()).select_from(TaskEvent).where(
                    TaskEvent.task_id.in_(task_ids)
                )
            ),
            "task_dependencies": self._count(
                select(func.count()).select_from(TaskDependency).where(
                    or_(
                        TaskDependency.task_id.in_(task_ids),
                        TaskDependency.depends_on_task_id.in_(task_ids),
                    )
                )
            ),
            "evidence_items": self._count(
                select(func.count()).select_from(EvidenceItem).where(
                    or_(
                        EvidenceItem.feedback_id.in_(feedback_ids),
                        EvidenceItem.task_id.in_(task_ids),
                    )
                )
            ),
            "daily_states": self._count(
                select(func.count()).select_from(DailyState).where(
                    DailyState.user_id == user_id,
                    DailyState.data_origin == SYNTHETIC,
                )
            ),
            "prediction_snapshots": self._count(
                select(func.count()).select_from(PredictionSnapshot).where(
                    PredictionSnapshot.user_id == user_id,
                    PredictionSnapshot.data_origin == SYNTHETIC,
                )
            ),
            "prediction_outcomes": self._count(
                select(func.count()).select_from(PredictionOutcome).where(
                    PredictionOutcome.task_id.in_(task_ids)
                )
            ),
        }

    def has_synthetic(self, user_id: int) -> bool:
        return sum(self.counts(user_id).values()) > 0

    def has_real_observations(self, user_id: int) -> bool:
        executions = self._count(
            select(func.count()).select_from(TaskExecution).where(
                TaskExecution.user_id == user_id, TaskExecution.data_origin == "real"
            )
        )
        feedbacks = self._count(
            select(func.count()).select_from(Feedback).where(
                Feedback.user_id == user_id, Feedback.data_origin == "real"
            )
        )
        return executions + feedbacks > 0

    def has_real_trait(self, user_id: int) -> bool:
        return bool(
            self._count(
                select(func.count()).select_from(TraitAssessmentModel).where(
                    TraitAssessmentModel.user_id == user_id,
                    TraitAssessmentModel.status == "completed",
                    TraitAssessmentModel.data_origin == "real",
                )
            )
        )

    def count_shadow(self, user_id: int, *, data_origin: str | None = None) -> int:
        stmt = select(func.count()).select_from(ShadowPrediction).where(
            ShadowPrediction.user_id == user_id
        )
        if data_origin is not None:
            stmt = stmt.where(ShadowPrediction.data_origin == data_origin)
        return self._count(stmt)

    def delete_for_user(self, user_id: int) -> dict[str, int]:
        plan_ids = self._plan_ids(user_id)
        task_ids = self._task_ids(user_id)
        feedback_ids = select(Feedback.id).where(
            Feedback.user_id == user_id, Feedback.data_origin == SYNTHETIC
        )
        deleted: dict[str, int] = {}

        deleted["prediction_outcomes"] = (
            self._session.execute(
                delete(PredictionOutcome).where(PredictionOutcome.task_id.in_(task_ids))
            ).rowcount
            or 0
        )
        deleted["prediction_snapshots"] = (
            self._session.execute(
                delete(PredictionSnapshot).where(
                    PredictionSnapshot.user_id == user_id,
                    PredictionSnapshot.data_origin == SYNTHETIC,
                )
            ).rowcount
            or 0
        )
        deleted["task_events"] = (
            self._session.execute(
                delete(TaskEvent).where(TaskEvent.task_id.in_(task_ids))
            ).rowcount
            or 0
        )
        deleted["task_dependencies"] = (
            self._session.execute(
                delete(TaskDependency).where(
                    or_(
                        TaskDependency.task_id.in_(task_ids),
                        TaskDependency.depends_on_task_id.in_(task_ids),
                    )
                )
            ).rowcount
            or 0
        )
        deleted["evidence_items"] = (
            self._session.execute(
                delete(EvidenceItem).where(
                    or_(
                        EvidenceItem.feedback_id.in_(feedback_ids),
                        EvidenceItem.task_id.in_(task_ids),
                    )
                )
            ).rowcount
            or 0
        )
        deleted["daily_states"] = (
            self._session.execute(
                delete(DailyState).where(
                    DailyState.user_id == user_id,
                    DailyState.data_origin == SYNTHETIC,
                )
            ).rowcount
            or 0
        )
        deleted["task_standards"] = (
            self._session.execute(
                delete(TaskStandard).where(TaskStandard.task_id.in_(task_ids))
            ).rowcount
            or 0
        )
        deleted["task_executions"] = (
            self._session.execute(
                delete(TaskExecution).where(
                    TaskExecution.user_id == user_id,
                    TaskExecution.data_origin == SYNTHETIC,
                )
            ).rowcount
            or 0
        )
        deleted["feedbacks"] = (
            self._session.execute(
                delete(Feedback).where(
                    Feedback.user_id == user_id, Feedback.data_origin == SYNTHETIC
                )
            ).rowcount
            or 0
        )
        deleted["prediction_logs"] = (
            self._session.execute(
                delete(PredictionLog).where(
                    PredictionLog.user_id == user_id,
                    PredictionLog.data_origin == SYNTHETIC,
                )
            ).rowcount
            or 0
        )
        deleted["shadow_predictions"] = (
            self._session.execute(
                delete(ShadowPrediction).where(
                    ShadowPrediction.user_id == user_id,
                    ShadowPrediction.data_origin == SYNTHETIC,
                )
            ).rowcount
            or 0
        )
        deleted["replan_events"] = (
            self._session.execute(
                delete(ReplanEvent).where(ReplanEvent.plan_id.in_(plan_ids))
            ).rowcount
            or 0
        )
        deleted["tasks"] = (
            self._session.execute(delete(Task).where(Task.id.in_(task_ids))).rowcount or 0
        )
        deleted["plans"] = (
            self._session.execute(
                delete(Plan).where(
                    Plan.user_id == user_id, Plan.data_origin == SYNTHETIC
                )
            ).rowcount
            or 0
        )
        deleted["trait_assessments"] = (
            self._session.execute(
                delete(TraitAssessmentModel).where(
                    TraitAssessmentModel.user_id == user_id,
                    TraitAssessmentModel.data_origin == SYNTHETIC,
                )
            ).rowcount
            or 0
        )
        self._session.flush()
        return deleted


__all__ = ["SyntheticDataRepository"]