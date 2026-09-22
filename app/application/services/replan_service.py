"""Replan policy: the per-user cooldown that guards manual replanning.

This service owns **eligibility only**. The replan itself is executed by the
agent (``PlanService.replan_with_agent`` → graph B), so there is exactly one
replan implementation in the codebase.

Cooldown is per-user (not per-plan): after any replan, no further replan is
allowed until ``SCHEDULER_MIN_REPLAN_INTERVAL_HOURS`` has elapsed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.application.dto.replan import ReplanEligibility
from app.application.exceptions import NotFoundError, PermissionDeniedError
from app.core.config import get_settings
from app.domain.models import Plan
from app.infrastructure.database.repositories import PlanRepository, ReplanEventRepository


class ReplanService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._plans = PlanRepository(session)
        self._events = ReplanEventRepository(session)
        self._settings = get_settings()

    def check_eligibility(self, user_id: int, plan_id: int) -> ReplanEligibility:
        """Can this user replan right now?

        Raises ``NotFoundError`` / ``PermissionDeniedError`` for unknown or
        foreign plans, so it doubles as the ownership check.
        """
        self._require_plan(user_id, plan_id)

        latest = self._events.get_latest_for_user(user_id)
        cooldown = self._settings.scheduler_min_replan_interval_hours
        if latest is None or latest.created_at is None:
            return ReplanEligibility(
                eligible=True, reason="no previous replan", cooldown_hours=cooldown
            )

        last_at = latest.created_at
        if last_at.tzinfo is None:  # sqlite may return naive datetimes
            last_at = last_at.replace(tzinfo=UTC)
        next_at = last_at + timedelta(hours=cooldown)
        now = datetime.now(UTC)

        if now >= next_at:
            return ReplanEligibility(
                eligible=True,
                reason="cooldown elapsed",
                last_replan_at=last_at,
                next_eligible_at=next_at,
                cooldown_hours=cooldown,
            )
        return ReplanEligibility(
            eligible=False,
            reason=f"cooldown active until {next_at.isoformat()}",
            last_replan_at=last_at,
            next_eligible_at=next_at,
            cooldown_hours=cooldown,
        )

    def _require_plan(self, user_id: int, plan_id: int) -> Plan:
        plan = self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError("plan not found")
        if plan.user_id != user_id:
            raise PermissionDeniedError("plan belongs to another user")
        return plan


__all__ = ["ReplanService"]
