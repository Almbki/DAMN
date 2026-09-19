"""Insight service: read-only analytics over a plan's real execution data."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

from sqlalchemy.orm import Session

from app.application.dto.insight import DailyCompletion, InsightReport
from app.application.exceptions import NotFoundError, PermissionDeniedError
from app.domain.models.enums import CognitiveLoad, TaskStatus
from app.infrastructure.database.repositories import (
    FeedbackRepository,
    PlanRepository,
    TaskExecutionRepository,
    TaskRepository,
)


class InsightService:
    def __init__(self, session: Session) -> None:
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._feedback = FeedbackRepository(session)

    def get_insights(self, user_id: int, plan_id: int) -> InsightReport:
        plan = self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError("plan not found")
        if plan.user_id != user_id:
            raise PermissionDeniedError("plan belongs to another user")

        tasks = self._tasks.list_by_plan(plan_id)
        task_ids = {task.id for task in tasks}
        executions = [e for e in self._executions.list_by_user(user_id) if e.task_id in task_ids]
        feedback = self._feedback.list_by_plan(plan_id)

        completed = [task for task in tasks if task.status == TaskStatus.COMPLETED]
        planned_minutes = sum(task.estimated_duration for task in tasks)
        actual_minutes = sum(e.actual_duration or 0 for e in executions)

        breakdown: dict[str, int] = defaultdict(int)
        high_cognitive_minutes = 0
        daily: dict[str, DailyCompletion] = {}
        for task in tasks:
            breakdown[task.cognitive_load.value] += 1
            if task.cognitive_load == CognitiveLoad.HIGH:
                high_cognitive_minutes += task.estimated_duration
            if task.scheduled_date is not None:
                key = task.scheduled_date.isoformat()
                entry = daily.setdefault(
                    key,
                    DailyCompletion(date=key, planned_minutes=0),
                )
                entry.total_tasks += 1
                entry.planned_minutes += task.estimated_duration
                if task.status == TaskStatus.COMPLETED:
                    entry.completed_tasks += 1

        for entry in daily.values():
            entry.completion_rate = (
                round(entry.completed_tasks / entry.total_tasks, 3) if entry.total_tasks else 0.0
            )

        stress_values = [f.stress_level for f in feedback if f.stress_level is not None]
        energy_values = [f.energy_level for f in feedback if f.energy_level is not None]

        planned_sum = sum((e.planned_duration or 0) for e in executions)
        actual_sum = sum((e.actual_duration or 0) for e in executions)
        ratio = round(actual_sum / planned_sum, 3) if planned_sum else None

        return InsightReport(
            plan_id=plan_id,
            total_tasks=len(tasks),
            completed_tasks=len(completed),
            completion_rate=round(len(completed) / len(tasks), 3) if tasks else 0.0,
            total_planned_minutes=planned_minutes,
            total_actual_minutes=actual_minutes,
            avg_stress=round(mean(stress_values), 2) if stress_values else None,
            avg_energy=round(mean(energy_values), 2) if energy_values else None,
            high_cognitive_minutes=high_cognitive_minutes,
            predicted_vs_actual_ratio=ratio,
            cognitive_load_breakdown=dict(breakdown),
            daily=sorted(daily.values(), key=lambda d: d.date),
            recommendations=self._recommendations(
                ratio=ratio,
                completion_rate=round(len(completed) / len(tasks), 3) if tasks else 0.0,
                avg_stress=mean(stress_values) if stress_values else None,
            ),
        )

    @staticmethod
    def _recommendations(
        *, ratio: float | None, completion_rate: float, avg_stress: float | None
    ) -> list[str]:
        notes: list[str] = []
        if ratio is not None and ratio > 1.3:
            notes.append(
                "Actual duration is well above planned - the duration factor should be raised."
            )
        if ratio is not None and ratio < 0.7:
            notes.append("Tasks finish faster than planned - the duration factor can be lowered.")
        if completion_rate < 0.5:
            notes.append("Completion rate is low - consider reducing daily load or replanning.")
        if avg_stress is not None and avg_stress >= 7:
            notes.append("Stress is high - reduce high-cognitive tasks per day.")
        return notes
