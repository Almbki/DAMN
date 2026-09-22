"""``user_statistics`` tool - deterministic aggregates over the planning context.

Pure arithmetic; no LLM, no database. Used by the adjustment router and by the
replanning prompt as evidence.
"""

from __future__ import annotations

from statistics import mean

from pydantic import BaseModel, Field

from app.agent.context import PlanningContext, UserPreferences
from app.agent.tools.base import BaseTool

_WINDOW = 7


class UserStatistics(BaseModel):
    """Aggregated execution statistics for the current user."""

    days_with_feedback: int = 0
    recent_completion_rate: float | None = None
    recent_stress: float | None = None
    recent_energy: float | None = None
    completion_trend: float | None = None
    planned_minutes: int = 0
    planned_high_cognitive_minutes: int = 0
    daily_limit_minutes: int = 300
    overload_ratio: float | None = None
    notes: list[str] = Field(default_factory=list)


class UserStatisticsInput(BaseModel):
    context: PlanningContext
    preferences: UserPreferences | None = None


class UserStatisticsTool(BaseTool[UserStatisticsInput, UserStatistics]):
    name = "user_statistics"
    description = (
        "Compute recent completion / stress / energy averages, completion trend "
        "and planned load from the user context."
    )
    llm_exposed = False

    def run(self, payload: UserStatisticsInput) -> UserStatistics:
        context = payload.context
        signals = context.recent_feedback[-_WINDOW:]
        stats = UserStatistics(days_with_feedback=len(signals))

        if signals:
            stats.recent_completion_rate = round(
                mean(signal.completion_rate for signal in signals), 4
            )
            stress = [s.stress_level for s in signals if s.stress_level is not None]
            energy = [s.energy_level for s in signals if s.energy_level is not None]
            stats.recent_stress = round(mean(stress), 2) if stress else None
            stats.recent_energy = round(mean(energy), 2) if energy else None
            if len(signals) >= 4:
                half = len(signals) // 2
                early = mean(s.completion_rate for s in signals[:half])
                late = mean(s.completion_rate for s in signals[half:])
                stats.completion_trend = round(late - early, 4)

        preferences = payload.preferences or context.preferences
        stats.daily_limit_minutes = preferences.daily_limit_minutes

        plan = context.current_plan
        if plan is not None:
            pending = plan.pending_tasks()
            stats.planned_minutes = sum(task.estimated_duration for task in plan.tasks)
            stats.planned_high_cognitive_minutes = sum(
                task.estimated_duration
                for task in pending
                if getattr(task.cognitive_load, "value", task.cognitive_load) == "high"
            )
            if preferences.available_minutes_per_day > 0 and pending:
                days = max(len({t.scheduled_date for t in pending if t.scheduled_date}), 1)
                stats.overload_ratio = round(
                    sum(t.estimated_duration for t in pending)
                    / (days * preferences.available_minutes_per_day),
                    3,
                )

        if stats.overload_ratio is not None and stats.overload_ratio > 1.0:
            stats.notes.append("planned load exceeds available capacity")
        if stats.completion_trend is not None and stats.completion_trend < -0.2:
            stats.notes.append("completion is trending down")
        return stats

    def summarize(self, value: UserStatistics) -> str:
        rate = value.recent_completion_rate
        return (
            f"{value.days_with_feedback} day(s) of feedback, "
            f"completion={rate if rate is not None else 'n/a'}"
        )


__all__ = ["UserStatistics", "UserStatisticsInput", "UserStatisticsTool"]
