"""Profile service - the user portrait engine's application-layer home.

Owns three things:

1. **Static portrait** (``users.mbti_type`` / ``mbti_dims`` / ``identity``) -
   read and updated here. MBTI is a SOFT self-report input, never a diagnosis.
2. **Adaptive state** (``user_states``, one row per user) - initialised from the
   MBTI template by the pure engine and updated by EWMA as feedback arrives.
3. **ML features** - maps the state onto :class:`UserFeatureSet`, so the
   predictors are driven by the portrait instead of a separate statistical
   aggregation. (This replaces the retired ``user_models`` table.)

The engine (``app/domain/profile``) is pure and does all the maths; this service
only does persistence and wiring.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from statistics import mean

from sqlalchemy.orm import Session

from app.application.exceptions import NotFoundError
from app.domain.models import User
from app.domain.profile import (
    ReplanDecision,
    UserProfileData,
    UserStateData,
    init_state,
    profile_prompt_json,
    replan_decision,
    resolve_mbti_type,
    update_state,
)
from app.infrastructure.database.repositories import (
    FeedbackRepository,
    TaskExecutionRepository,
    UserRepository,
    UserStateRepository,
)
from app.ml.base import UserFeatureSet

#: Trailing windows used for the completion-rate features.
WINDOW_7D = 7
WINDOW_30D = 30
#: Profile fields that can be updated through the API.
PROFILE_FIELDS: tuple[str, ...] = ("mbti_type", "mbti_dims", "identity")


class ProfileService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._states = UserStateRepository(session)
        self._feedback = FeedbackRepository(session)
        self._executions = TaskExecutionRepository(session)

    # ------------------------------------------------------------------
    # static portrait
    # ------------------------------------------------------------------
    def _require_user(self, user_id: int) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("user not found")
        return user

    def get_profile(self, user_id: int) -> UserProfileData:
        """Static portrait; all fields ``None`` when the user has not set one."""
        user = self._require_user(user_id)
        return self._to_profile_data(user)

    def is_configured(self, user_id: int) -> bool:
        """True when the user has supplied at least one portrait field."""
        profile = self.get_profile(user_id)
        return any(
            getattr(profile, field) is not None for field in ("mbti_type", "mbti_dims", "identity")
        )

    def upsert_profile(
        self,
        user_id: int,
        *,
        provided: set[str],
        mbti_type: str | None = None,
        mbti_dims: dict[str, float] | None = None,
        identity: str | None = None,
    ) -> UserStateData:
        """Update the portrait and **re-initialise** the adaptive state.

        Field semantics (agreed with the frontend):

        * a field absent from ``provided`` keeps its stored value;
        * a field explicitly set to ``None`` clears it;
        * changing the portrait resets the state from the MBTI template
          (``update_count = 0``), because the initial values all come from it.
        """
        self._require_user(user_id)
        incoming = {"mbti_type": mbti_type, "mbti_dims": mbti_dims, "identity": identity}
        updates: dict[str, object] = {
            field: incoming[field] for field in PROFILE_FIELDS if field in provided
        }
        if "mbti_type" in updates and updates["mbti_type"] is not None:
            updates["mbti_type"] = str(updates["mbti_type"]).strip().upper() or None
        if updates:
            self._users.update_fields(user_id, **updates)

        user = self._require_user(user_id)
        state = init_state(self._to_profile_data(user))
        saved = self._states.upsert(user_id, state)
        self._session.commit()
        return saved

    # ------------------------------------------------------------------
    # adaptive state
    # ------------------------------------------------------------------
    def get_state(self, user_id: int) -> UserStateData:
        """Current adaptive state; lazily initialised from the portrait."""
        self._require_user(user_id)
        existing = self._states.get_by_user(user_id)
        if existing is not None:
            return existing
        user = self._require_user(user_id)
        created = self._states.upsert(user_id, init_state(self._to_profile_data(user)))
        self._session.commit()
        return created

    def update_from_feedback(
        self,
        user_id: int,
        *,
        completed: bool | None = None,
        partial_pct: float | None = None,
        actual_min: float | None = None,
        theoretical_min: float | None = None,
        energy_after: float | None = None,
        stress_after: float | None = None,
    ) -> UserStateData:
        """Feed one observation through the EWMA update and persist it."""
        current = self.get_state(user_id)
        updated = update_state(
            current,
            completed=completed,
            partial_pct=partial_pct,
            actual_min=actual_min,
            theoretical_min=theoretical_min,
            energy_after=energy_after,
            stress_after=stress_after,
        )
        saved = self._states.upsert(user_id, updated)
        self._session.commit()
        return saved

    def recent_completion_rates(self, user_id: int, *, days: int = 7) -> list[float]:
        """Per-day completion rates (oldest first) over the trailing window."""
        cutoff = datetime.now(UTC).date() - timedelta(days=days - 1)
        by_day: dict = {}
        for item in self._feedback.list_by_user(user_id, limit=500):
            if item.date >= cutoff:
                by_day[item.date] = item.completion_rate
        return [by_day[day] for day in sorted(by_day)]

    def replan_decision_for(self, user_id: int, *, duration_bias: float = 0.0) -> ReplanDecision:
        """Portrait-driven replan verdict for the backend's adjustment router."""
        state = self.get_state(user_id)
        rates = self.recent_completion_rates(user_id, days=5)
        if state.update_count == 0 and not rates:
            return ReplanDecision(decision="none", reason_code="no_history")
        return replan_decision(rates, duration_bias)

    def duration_bias(self, user_id: int) -> float:
        """Share of recent executions that overran their planned duration."""
        executions = self._executions.list_by_user(user_id, limit=50)
        ratios = [
            (e.actual_duration or 0) / e.planned_duration
            for e in executions
            if e.planned_duration and e.actual_duration
        ]
        if not ratios:
            return 0.0
        return round(sum(1 for ratio in ratios if ratio > 1.15) / len(ratios), 4)

    # ------------------------------------------------------------------
    # features / snapshot
    # ------------------------------------------------------------------
    def build_user_features(self, user_id: int) -> UserFeatureSet:
        """Map the portrait state onto the ML feature contract.

        Scale conversions: the state stores 0..1, the feature contract uses
        0..10 for stress/energy.
        """
        user = self._require_user(user_id)
        state = self.get_state(user_id)
        feedbacks = self._feedback.list_by_user(user_id, limit=200)

        def window_rate(days: int) -> float | None:
            rates = self.recent_completion_rates(user_id, days=days)
            return round(mean(rates), 4) if rates else None

        sleep = [f.sleep_hours for f in feedbacks if f.sleep_hours is not None]
        return UserFeatureSet(
            user_id=user_id,
            duration_factor=round(state.duration_factor, 4),
            completion_rate_7d=window_rate(WINDOW_7D) or round(state.completion_prob, 4),
            completion_rate_30d=window_rate(WINDOW_30D) or round(state.completion_prob, 4),
            avg_stress=round(state.stress_baseline * 10.0, 2),
            avg_energy=round(state.state_energy * 10.0, 2),
            sleep_hours=round(mean(sleep), 2) if sleep else None,
            preferred_time_slots=dict(state.preferred_time_slots),
            sample_size=state.update_count,
            execution_weight=user.execution_weight,
        )

    def snapshot(self, user_id: int) -> dict:
        """Portrait + state as one JSON-serialisable dict (API and prompt)."""
        profile = self.get_profile(user_id)
        state = self.get_state(user_id)
        payload = profile_prompt_json(profile, state)
        payload["mbti_dims"] = dict(profile.mbti_dims or {}) or None
        payload["degraded"] = state.is_degraded()
        return payload

    def prompt_block(self, user_id: int) -> dict:
        """Same as :meth:`snapshot` but safe to embed in an LLM prompt."""
        return self.snapshot(user_id)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    @staticmethod
    def _to_profile_data(user: User) -> UserProfileData:
        return UserProfileData(
            mbti_type=user.mbti_type,
            mbti_dims=dict(user.mbti_dims) if user.mbti_dims else None,
            identity=user.identity,
        )

    def resolved_mbti(self, user_id: int) -> str:
        return resolve_mbti_type(self.get_profile(user_id))


__all__ = ["PROFILE_FIELDS", "ProfileService", "WINDOW_7D", "WINDOW_30D"]
