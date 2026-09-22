"""Episodic memory: concrete things that happened (executions, daily feedback)."""

from __future__ import annotations

from app.agent.context import MemoryItem, MemoryKind
from app.domain.models import Feedback, TaskExecution


def build_episodic_memory(
    executions: list[TaskExecution],
    feedbacks: list[Feedback],
    *,
    execution_limit: int = 10,
    feedback_limit: int = 7,
) -> list[MemoryItem]:
    """Derive recent, dated execution events (most recent first)."""
    items: list[MemoryItem] = []

    for execution in sorted(
        executions, key=lambda item: item.created_at, reverse=True
    )[:execution_limit]:
        ratio = None
        if execution.planned_duration:
            ratio = round((execution.actual_duration or 0) / execution.planned_duration, 2)
        items.append(
            MemoryItem(
                kind=MemoryKind.EPISODIC,
                key=f"execution:{execution.task_id}:{execution.created_at.date()}",
                value={
                    "task_id": execution.task_id,
                    "planned_minutes": execution.planned_duration,
                    "actual_minutes": execution.actual_duration,
                    "completion_rate": execution.completion_rate,
                    "difficulty": execution.difficulty_feedback,
                    "completed": execution.completed,
                    "time_of_day": getattr(execution.time_of_day, "value", execution.time_of_day),
                },
                summary=(
                    f"task {execution.task_id} on {execution.created_at.date()}: "
                    f"completed={execution.completed}"
                    + (f", took {ratio}x planned" if ratio is not None else "")
                ),
                confidence=0.8,
                source="task_executions",
            )
        )

    for feedback in sorted(feedbacks, key=lambda item: item.date, reverse=True)[:feedback_limit]:
        items.append(
            MemoryItem(
                kind=MemoryKind.EPISODIC,
                key=f"feedback:{feedback.date}",
                value={
                    "date": feedback.date.isoformat(),
                    "completion_rate": feedback.completion_rate,
                    "stress": feedback.stress_level,
                    "energy": feedback.energy_level,
                    "delay_reason": feedback.delay_reason,
                    "sleep_hours": feedback.sleep_hours,
                },
                summary=(
                    f"{feedback.date}: completion {feedback.completion_rate:.0%}, "
                    f"stress {feedback.stress_level}, energy {feedback.energy_level}"
                ),
                confidence=0.9,
                source="feedbacks",
            )
        )
    return items


__all__ = ["build_episodic_memory"]
