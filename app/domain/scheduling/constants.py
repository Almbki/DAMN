"""Single source of truth for scheduling horizon constants."""

from __future__ import annotations

#: Default planning horizon (days past ``start_date``). Used by the API when the
#: client omits an end date, by PlanService fallbacks and by the Scheduler.
DEFAULT_HORIZON_DAYS = 13

#: HARD scheduler/rule failure code: one goal has too many minutes on one day.
GOAL_DAILY_CAPACITY_EXCEEDED = "GOAL_DAILY_CAPACITY_EXCEEDED"

__all__ = ["DEFAULT_HORIZON_DAYS", "GOAL_DAILY_CAPACITY_EXCEEDED"]