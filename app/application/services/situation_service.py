"""Situation trend service - the profile page's curve and its justification.

Reads ``feedbacks`` (self-reported energy / stress) over a window and derives
``efficacy``. The frontend used to compute efficacy itself as
``0.6 * execution_weight + 0.4 * recent completion rate``; the backend now
returns the same formula so both sides agree, and the frontend prefers
``points[].efficacy`` when present.
"""

from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from sqlalchemy.orm import Session

from app.domain.models.enums import TimeOfDay
from app.infrastructure.database.repositories import (
    FeedbackRepository,
    TaskExecutionRepository,
    UserRepository,
)
from app.schemas.user import SituationTrendPoint, SituationTrendRead

#: Days of history needed before the trend is considered trustworthy.
MIN_SAMPLES = 7
#: Efficacy weighting (documented, mirrored by the frontend fallback).
EXECUTION_WEIGHT = 0.6
COMPLETION_WEIGHT = 0.4
#: Window bounds for the `days` query parameter.
MIN_DAYS = 2
MAX_DAYS = 90


class SituationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._feedback = FeedbackRepository(session)
        self._executions = TaskExecutionRepository(session)

    def get_trends(self, user_id: int, *, days: int = 14) -> SituationTrendRead:
        days = max(MIN_DAYS, min(MAX_DAYS, int(days)))
        end = date.today()
        start = end - timedelta(days=days - 1)

        feedbacks = [
            item
            for item in self._feedback.list_by_user(user_id, limit=1000)
            if start <= item.date <= end
        ]
        by_day: dict[date, list] = {}
        for item in feedbacks:
            by_day.setdefault(item.date, []).append(item)

        recent_completion = (
            mean(item.completion_rate for item in feedbacks) if feedbacks else 0.0
        )
        user = self._users.get_by_id(user_id)
        execution_weight = user.execution_weight if user else 0.5
        efficacy = round(
            EXECUTION_WEIGHT * execution_weight + COMPLETION_WEIGHT * recent_completion, 4
        )

        points: list[SituationTrendPoint] = []
        for offset in range(days):
            day = start + timedelta(days=offset)
            entries = by_day.get(day, [])
            energy = [e.energy_level for e in entries if e.energy_level is not None]
            stress = [e.stress_level for e in entries if e.stress_level is not None]
            points.append(
                SituationTrendPoint(
                    date=day,
                    energy=round(mean(energy), 2) if energy else None,
                    stress=round(mean(stress), 2) if stress else None,
                    efficacy=efficacy if entries else None,
                )
            )

        samples = len(feedbacks)
        sufficient = samples >= MIN_SAMPLES
        return SituationTrendRead(
            points=points,
            samples=samples,
            min_samples=MIN_SAMPLES,
            sufficient=sufficient,
            drivers=self._drivers(
                samples=samples,
                sufficient=sufficient,
                recent_completion=recent_completion,
                efficacy=efficacy,
                feedbacks=feedbacks,
                user_id=user_id,
            ),
        )

    def _drivers(
        self,
        *,
        samples: int,
        sufficient: bool,
        recent_completion: float,
        efficacy: float,
        feedbacks: list,
        user_id: int,
    ) -> list[str]:
        """Human-readable reasons for the profile page (Chinese UI copy)."""
        drivers = [
            f"近 {samples} 天共 {samples} 条反馈，"
            f"{'数据量已足够' if sufficient else f'少于 {MIN_SAMPLES} 条，结论仅供参考'}。",
            f"近期平均完成率 {recent_completion:.0%}，效能指数 {efficacy:.2f}。",
        ]

        stresses = [f.stress_level for f in feedbacks if f.stress_level is not None]
        energies = [f.energy_level for f in feedbacks if f.energy_level is not None]
        if stresses and mean(stresses) >= 7:
            drivers.append("平均压力偏高，建议下调每日任务量。")
        if energies and mean(energies) <= 3.5:
            drivers.append("平均精力偏低，建议缩短单次任务时长。")

        executions = self._executions.list_by_user(user_id, limit=200)
        by_slot: dict[str, list[float]] = {}
        for execution in executions:
            slot = getattr(execution.time_of_day, "value", execution.time_of_day)
            if slot:
                by_slot.setdefault(str(slot), []).append(execution.completion_rate)
        scored = {slot: mean(rates) for slot, rates in by_slot.items() if len(rates) >= 3}
        if scored:
            best = max(scored, key=lambda slot: scored[slot])
            worst = min(scored, key=lambda slot: scored[slot])
            if scored[best] - scored[worst] >= 0.2:
                drivers.append(
                    f"{self._label(best)}的完成率明显高于{self._label(worst)}，"
                    "可把重要任务安排在前者。"
                )
        return drivers

    @staticmethod
    def _label(slot: str) -> str:
        return {
            TimeOfDay.MORNING.value: "上午",
            TimeOfDay.AFTERNOON.value: "下午",
            TimeOfDay.EVENING.value: "晚上",
            TimeOfDay.NIGHT.value: "深夜",
        }.get(slot, slot)


__all__ = ["EXECUTION_WEIGHT", "MAX_DAYS", "MIN_DAYS", "MIN_SAMPLES", "SituationService"]
