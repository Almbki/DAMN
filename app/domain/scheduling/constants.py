"""Single source of truth for scheduling horizon constants."""

from __future__ import annotations

#: Default planning horizon (days past ``start_date``). Used by the API when the
#: client omits an end date, by PlanService fallbacks and by the Scheduler.
DEFAULT_HORIZON_DAYS = 13

__all__ = ["DEFAULT_HORIZON_DAYS"]