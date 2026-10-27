"""HARD: one goal's total scheduled minutes per day must respect its cap."""

from __future__ import annotations

from datetime import date

from app.domain.models.enums import ViolationSeverity
from app.domain.rules.base import Rule, RuleContext, RuleViolation
from app.domain.scheduling.constants import GOAL_DAILY_CAPACITY_EXCEEDED
from app.domain.scheduling.schedule_result import CandidateSchedule


class GoalDailyCapacityRule(Rule):
    """HARD: ``sum(minutes) per (goal, day) <= max_daily_minutes_per_goal``.

    The cap is per goal and per day. Different goals have independent budgets;
    recurring occurrences and project chunks all count toward their goal.
    """

    name = "goal_daily_capacity"
    severity: ViolationSeverity = ViolationSeverity.HARD

    def validate(
        self, schedule: CandidateSchedule, context: RuleContext
    ) -> list[RuleViolation]:
        totals: dict[tuple[int, date], int] = {}
        task_ids: dict[tuple[int, date], list[int]] = {}
        for task in schedule.tasks:
            if task.goal_id is None:
                continue
            key = (task.goal_id, task.scheduled_date)
            totals[key] = totals.get(key, 0) + task.duration_minutes
            task_ids.setdefault(key, []).append(task.task_id)

        violations: list[RuleViolation] = []
        for (goal_id, day), minutes in sorted(totals.items()):
            if minutes <= context.max_daily_minutes_per_goal:
                continue
            violations.append(
                self._violation(
                    f"Goal {goal_id} has {minutes} minutes on "
                    f"{day.isoformat()}, over the per-goal daily cap "
                    f"{context.max_daily_minutes_per_goal}.",
                    task_ids=task_ids[(goal_id, day)],
                    code=GOAL_DAILY_CAPACITY_EXCEEDED,
                )
            )
        return violations


__all__ = ["GoalDailyCapacityRule"]
