"""Profile service - application home of the three-layer user model.

The old EWMA portrait engine is no longer a runtime source of truth:

* **Level 1** (``users.trait_profile``) is the authoritative stable-trait record.
* **Level 2** (``user_states.level2_profile``) is the authoritative dynamic
  state, produced by replaying DDSR-V1 over real feedback/execution history.
* The legacy ``user_states`` float columns remain as **display projections** and
  API compatibility fields only; no code derives a second state from them.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from statistics import mean

from sqlalchemy.orm import Session

from app.agent.features import UserFeatureSet
from app.application.exceptions import NotFoundError
from app.application.services.user_model_service import UserModelService
from app.domain.models import User
from app.domain.profile import UserProfileData, UserStateData
from app.infrastructure.database.repositories import (
    FeedbackRepository,
    TaskExecutionRepository,
    UserRepository,
    UserStateRepository,
)
from app.user_models.contracts import DynamicStateSnapshot
from app.user_models.runtime import UserModelRuntime

WINDOW_7D = 7
WINDOW_30D = 30
PROFILE_FIELDS: tuple[str, ...] = ("identity",)


class ProfileService:
    def __init__(
        self, session: Session, *, runtime: UserModelRuntime | None = None
    ) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._states = UserStateRepository(session)
        self._feedback = FeedbackRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._user_models = UserModelService(session, runtime=runtime)

    # ------------------------------------------------------------------
    # static portrait
    # ------------------------------------------------------------------
    def _require_user(self, user_id: int) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("user not found")
        return user

    def get_profile(self, user_id: int) -> UserProfileData:
        user = self._require_user(user_id)
        return self._to_profile_data(user)

    def is_configured(self, user_id: int) -> bool:
        user = self._require_user(user_id)
        profile = self._to_profile_data(user)
        return bool(user.trait_profile) or any(
            getattr(profile, field) is not None for field in PROFILE_FIELDS
        )

    def upsert_profile(
        self,
        user_id: int,
        *,
        provided: set[str],
        identity: str | None = None,
        trait_profile: dict | None = None,
    ) -> UserStateData:
        """Update the static portrait and/or import a validated Level 1 profile.

        Changing the portrait does not re-initialise Level 2: dynamic state comes
        from real observations, not from a personality template.
        """
        self._require_user(user_id)
        incoming = {"identity": identity}
        updates: dict[str, object] = {
            field: incoming[field] for field in PROFILE_FIELDS if field in provided
        }
        if updates:
            self._users.update_fields(user_id, **updates)
        if trait_profile is not None:
            self._user_models.set_trait_profile(user_id, trait_profile)
        self._session.commit()
        return self.get_state(user_id)

    # ------------------------------------------------------------------
    # Level 1 / Level 2 access
    # ------------------------------------------------------------------
    def get_trait_profile(self, user_id: int) -> dict | None:
        return self._user_models.get_trait_profile(user_id)

    def set_trait_profile(self, user_id: int, profile: dict) -> dict:
        payload = self._user_models.set_trait_profile(user_id, profile)
        self._session.commit()
        return payload

    def refresh_dynamic_state(self, user_id: int) -> DynamicStateSnapshot | None:
        return self._user_models.refresh_dynamic_state(user_id)

    def get_state(self, user_id: int) -> UserStateData:
        """Level 2 projections, or neutral defaults when no state exists yet."""
        self._require_user(user_id)
        existing = self._states.get_by_user(user_id)
        if existing is None:
            return UserStateData()
        return _project_level2(existing)

    def model_context(self, user_id: int):
        return self._user_models.context(user_id)

    def model_runtime_description(self) -> dict:
        return self._user_models.describe()

    def shadow_summary(self, user_id: int) -> dict:
        return self._user_models.shadow_summary(user_id)

    # ------------------------------------------------------------------
    # Aggregates / features (observed, not predicted)
    # ------------------------------------------------------------------
    def recent_completion_rates(self, user_id: int, *, days: int = 7) -> list[float]:
        cutoff = datetime.now(UTC).date() - timedelta(days=days - 1)
        by_day: dict = {}
        for item in self._feedback.list_by_user(user_id, limit=500):
            if item.date >= cutoff:
                by_day[item.date] = item.completion_rate
        return [by_day[day] for day in sorted(by_day)]

    def duration_bias(self, user_id: int) -> float:
        executions = self._executions.list_by_user(user_id, limit=50)
        ratios = [
            (e.actual_duration or 0) / e.planned_duration
            for e in executions
            if e.planned_duration and e.actual_duration
        ]
        if not ratios:
            return 0.0
        return round(sum(1 for ratio in ratios if ratio > 1.15) / len(ratios), 4)

    def build_user_features(self, user_id: int) -> UserFeatureSet:
        user = self._require_user(user_id)
        state = self.get_state(user_id)
        feedbacks = self._feedback.list_by_user(user_id, limit=200)

        def window_rate(days: int) -> float | None:
            rates = self.recent_completion_rates(user_id, days=days)
            return round(mean(rates), 4) if rates else None

        sleep = [f.sleep_hours for f in feedbacks if f.sleep_hours is not None]
        has_level2 = state.level2_profile is not None
        return UserFeatureSet(
            user_id=user_id,
            completion_rate_7d=window_rate(WINDOW_7D),
            completion_rate_30d=window_rate(WINDOW_30D),
            avg_stress=round(state.state_stress * 10.0, 2) if has_level2 else None,
            avg_energy=round(state.state_energy * 10.0, 2) if has_level2 else None,
            sleep_hours=round(mean(sleep), 2) if sleep else None,
            preferred_time_slots=dict(state.preferred_time_slots),
            sample_size=state.update_count,
            execution_weight=user.execution_weight,
        )

    def snapshot(self, user_id: int) -> dict:
        """Model snapshot for prompts/API - never a second hidden state."""
        trait_profile = self.get_trait_profile(user_id)
        state_profile = self._user_models.get_state_profile(user_id)
        context = self._user_models.context(user_id)
        return {
            "level1": context.trait.model_dump(mode="json") if context.trait else None,
            "level2": context.state.model_dump(mode="json") if context.state else None,
            "has_trait_profile": trait_profile is not None,
            "has_level2_profile": state_profile is not None,
            "degraded": context.degraded,
            "degraded_reasons": list(context.degraded_reasons),
            "level3_mode": context.level3_mode.value,
            "model_metadata": [
                meta.model_dump(mode="json") for meta in context.metadata
            ],
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    @staticmethod
    def _to_profile_data(user: User) -> UserProfileData:
        return UserProfileData(identity=user.identity)


def _project_level2(state: UserStateData) -> UserStateData:
    """Fill the query-friendly projections from the JSON source of truth."""
    payload = state.level2_profile
    if not payload:
        return state
    try:
        fatigue = float(payload["fatigue"]["value"])
        stress = float(payload["stress"]["value"])
        efficacy = float(payload["self_efficacy"]["value"])
        fatigue_unc = float(payload["fatigue"]["uncertainty"])
        stress_unc = float(payload["stress"]["uncertainty"])
        efficacy_unc = float(payload["self_efficacy"]["uncertainty"])
    except (KeyError, TypeError, ValueError):
        return state
    return UserStateData(
        duration_factor=state.duration_factor,
        completion_prob=state.completion_prob,
        stress_baseline=state.stress_baseline,
        energy_drain_rate=state.energy_drain_rate,
        proactive_score=state.proactive_score,
        procrastination_tendency=state.procrastination_tendency,
        preferred_time_slots=dict(state.preferred_time_slots),
        stress_response=state.stress_response,
        state_energy=round(max(0.0, min(1.0, 1.0 - fatigue)), 6),
        state_fatigue=round(fatigue, 6),
        self_efficacy=round(efficacy, 6),
        update_count=state.update_count,
        state_stress=round(stress, 6),
        state_fatigue_uncertainty=round(fatigue_unc, 6),
        state_stress_uncertainty=round(stress_unc, 6),
        self_efficacy_uncertainty=round(efficacy_unc, 6),
        level2_profile=dict(payload),
        level2_profile_date=state.level2_profile_date,
        level2_model_version=state.level2_model_version,
        level2_config_version=state.level2_config_version,
        level2_artifact_hash=state.level2_artifact_hash,
        level2_updated_at=state.level2_updated_at,
    )


__all__ = ["PROFILE_FIELDS", "ProfileService", "WINDOW_7D", "WINDOW_30D"]