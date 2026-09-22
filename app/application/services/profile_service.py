"""Profile service (环节 1 基础画像 + 环节 3 反馈回流).

Owns the transaction boundary for the two profile tables, mirroring the other
application services: repositories only ``flush()``, the service commits.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.services.user_model_service import UserModelService
from app.domain.profile import (
    MBTI_DIMENSIONS,
    UserProfileData,
    UserStateData,
    init_state,
    profile_prompt_json,
    update_state,
)
from app.infrastructure.database.models import UserProfileModel, UserStateModel
from app.infrastructure.database.repositories import (
    UserProfileRepository,
    UserStateRepository,
)
from app.ml.base import UserFeatureSet
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpsert,
    UserProfileRead,
    UserStateRead,
)


class ProfileService:
    """Reads/writes the static user profile and its dynamic feedback state."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._profiles = UserProfileRepository(session)
        self._states = UserStateRepository(session)

    # -- profile -----------------------------------------------------------
    def upsert_profile(
        self,
        user_id: int,
        data: ProfileUpsert,
        *,
        provided: set[str] | None = None,
    ) -> ProfileResponse:
        """Create or update the profile, then (re)initialise the state.

        Changing the profile resets the dynamic state (``update_count = 0``) per
        the 画像 spec - the template values are re-derived from scratch.

        ``provided`` lists which profile fields the caller explicitly submitted;
        ``None`` (register) means full-document overwrite. Within ``provided``,
        an explicit ``None`` value clears the column; fields not in ``provided``
        keep their existing values.
        """
        provided = provided or {"mbti_type", "mbti_dims", "identity"}
        existing = self._profiles.get_by_user_id(user_id)
        columns = self._profile_columns(data, existing, provided)
        if existing is None:
            profile_orm = self._profiles.create(user_id, **columns)
        else:
            for key, value in columns.items():
                setattr(existing, key, value)
            profile_orm = self._profiles.save(existing)

        profile_data = self._to_profile_data(profile_orm)
        state_data = init_state(profile_data)
        self._write_state(user_id, state_data)
        self._session.commit()
        return self._build_response(profile_orm, state_data)

    def get_profile(self, user_id: int) -> ProfileResponse | None:
        """Return the profile + state, or ``None`` when no profile row exists."""
        profile_orm = self._profiles.get_by_user_id(user_id)
        if profile_orm is None:
            return None
        profile_data = self._to_profile_data(profile_orm)
        state_orm = self._states.get_by_user_id(user_id)
        state_data = self._to_state_data(state_orm) if state_orm else init_state(profile_data)
        return self._build_response(profile_orm, state_data)

    # -- feedback loop -----------------------------------------------------
    def apply_feedback(
        self,
        user_id: int,
        *,
        actual_min: float | None = None,
        theoretical_min: float | None = None,
        completed: bool | None = None,
        partial_pct: float | None = None,
        energy_after: float | None = None,
        stress_after: float | None = None,
    ) -> UserStateData | None:
        """Fold one observation into the state (returns ``None`` without a row)."""
        state_orm = self._states.get_by_user_id(user_id)
        if state_orm is None:
            return None
        updated = update_state(
            self._to_state_data(state_orm),
            actual_min=actual_min,
            theoretical_min=theoretical_min,
            completed=completed,
            partial_pct=partial_pct,
            energy_after=energy_after,
            stress_after=stress_after,
        )
        for key, value in self._state_columns(updated).items():
            setattr(state_orm, key, value)
        self._states.save(state_orm)
        self._session.commit()
        return updated

    # -- prompt / features -------------------------------------------------
    def build_profile_prompt(self, user_id: int) -> dict | None:
        """Portrait JSON for 环节 2 prompt injection (``None`` without a profile)."""
        profile_orm = self._profiles.get_by_user_id(user_id)
        if profile_orm is None:
            return None
        profile_data = self._to_profile_data(profile_orm)
        state_orm = self._states.get_by_user_id(user_id)
        state_data = self._to_state_data(state_orm) if state_orm else init_state(profile_data)
        return profile_prompt_json(profile_data, state_data)

    def build_user_features(self, user_id: int) -> UserFeatureSet:
        """Feature set for the ML predictors.

        Starts from the existing statistical aggregation (history + feedback),
        then - when a state row exists - overrides the fields the adaptive
        profile owns: duration factor, energy/stress, slots and sample size.
        """
        features = UserModelService(self._session).get_user_features(user_id)
        state_orm = self._states.get_by_user_id(user_id)
        if state_orm is None:
            return features
        return features.model_copy(
            update={
                "duration_factor": round(state_orm.duration_factor, 4),
                "avg_energy": round(state_orm.state_energy * 10.0, 4),
                "avg_stress": round(state_orm.stress_baseline * 10.0, 4),
                "preferred_time_slots": dict(state_orm.preferred_time_slots or {}),
                "sample_size": state_orm.update_count,
            }
        )

    # -- persistence helpers ----------------------------------------------
    def _write_state(self, user_id: int, state_data: UserStateData) -> UserStateModel:
        state_orm = self._states.get_by_user_id(user_id)
        columns = self._state_columns(state_data)
        if state_orm is None:
            return self._states.create(user_id, **columns)
        for key, value in columns.items():
            setattr(state_orm, key, value)
        return self._states.save(state_orm)

    @staticmethod
    def _profile_columns(
        data: ProfileUpsert,
        existing: UserProfileModel | None,
        provided: set[str],
    ) -> dict:
        """Columns to write for the explicitly provided fields.

        ``mbti_dims`` is treated as one document: providing it replaces all four
        dimension columns (absent dims become ``None``). ``None`` values on a
        provided field clear the column.
        """
        del existing  # columns are decided solely by ``provided``
        columns: dict[str, object] = {}
        if "mbti_type" in provided:
            columns["mbti_type"] = data.mbti_type
        if "mbti_dims" in provided:
            dims = data.mbti_dims or {}
            for dim in MBTI_DIMENSIONS:
                columns[f"mbti_{dim}"] = dims.get(dim)
        if "identity" in provided:
            columns["identity"] = data.identity
        return columns

    @staticmethod
    def _state_columns(state: UserStateData) -> dict:
        return {
            "duration_factor": state.duration_factor,
            "completion_prob": state.completion_prob,
            "stress_baseline": state.stress_baseline,
            "energy_drain_rate": state.energy_drain_rate,
            "proactive_score": state.proactive_score,
            "procrastination_tendency": state.procrastination_tendency,
            "preferred_time_slots": dict(state.preferred_time_slots),
            "stress_response": state.stress_response,
            "state_energy": state.state_energy,
            "state_fatigue": state.state_fatigue,
            "self_efficacy": state.self_efficacy,
            "update_count": state.update_count,
        }

    @staticmethod
    def _to_profile_data(orm: UserProfileModel) -> UserProfileData:
        dims = {
            dim: getattr(orm, f"mbti_{dim}")
            for dim in MBTI_DIMENSIONS
            if getattr(orm, f"mbti_{dim}") is not None
        }
        return UserProfileData(
            mbti_type=orm.mbti_type,
            mbti_dims=dims or None,
            identity=orm.identity,
        )

    @staticmethod
    def _to_state_data(orm: UserStateModel) -> UserStateData:
        return UserStateData(
            duration_factor=orm.duration_factor,
            completion_prob=orm.completion_prob,
            stress_baseline=orm.stress_baseline,
            energy_drain_rate=orm.energy_drain_rate,
            proactive_score=orm.proactive_score,
            procrastination_tendency=orm.procrastination_tendency,
            preferred_time_slots=dict(orm.preferred_time_slots or {}),
            stress_response=orm.stress_response,
            state_energy=orm.state_energy,
            state_fatigue=orm.state_fatigue,
            self_efficacy=orm.self_efficacy,
            update_count=orm.update_count,
        )

    def _build_response(
        self, profile_orm: UserProfileModel, state_data: UserStateData
    ) -> ProfileResponse:
        return ProfileResponse(
            profile=UserProfileRead(
                mbti_type=profile_orm.mbti_type,
                mbti_dims=self._to_profile_data(profile_orm).mbti_dims,
                identity=profile_orm.identity,
            ),
            state=UserStateRead(
                duration_factor=state_data.duration_factor,
                completion_prob=state_data.completion_prob,
                stress_baseline=state_data.stress_baseline,
                energy_drain_rate=state_data.energy_drain_rate,
                proactive_score=state_data.proactive_score,
                procrastination_tendency=state_data.procrastination_tendency,
                preferred_time_slots=dict(state_data.preferred_time_slots),
                stress_response=state_data.stress_response,
                state_energy=state_data.state_energy,
                state_fatigue=state_data.state_fatigue,
                self_efficacy=state_data.self_efficacy,
                update_count=state_data.update_count,
                degraded=state_data.is_degraded(),
            ),
        )
