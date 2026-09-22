"""UserState persistence - one adaptive-state row per user.

Convention note: unlike the handed-over version, this repository returns the
**domain object** (``app.domain.profile.models.UserStateData``, the type the
profile engine consumes) instead of the ORM row, matching every other repository
in this project. There is deliberately only ONE state representation, so the
engine and the database cannot drift apart.
"""

from __future__ import annotations

from sqlalchemy import select

from app.domain.profile.models import UserStateData
from app.infrastructure.database.models.user_state import UserStateModel
from app.infrastructure.database.repositories.base import RepositoryBase

_FIELDS: tuple[str, ...] = (
    "duration_factor",
    "completion_prob",
    "stress_baseline",
    "energy_drain_rate",
    "proactive_score",
    "procrastination_tendency",
    "preferred_time_slots",
    "stress_response",
    "state_energy",
    "state_fatigue",
    "self_efficacy",
    "update_count",
)


class UserStateRepository(RepositoryBase):
    def get_by_user(self, user_id: int) -> UserStateData | None:
        orm = self._session.scalars(
            select(UserStateModel).where(UserStateModel.user_id == user_id).limit(1)
        ).first()
        if orm is None:
            return None
        return self._to_domain(orm)

    def upsert(self, user_id: int, state: UserStateData) -> UserStateData:
        """Create or update the single state row for this user."""
        orm = self._session.scalars(
            select(UserStateModel).where(UserStateModel.user_id == user_id).limit(1)
        ).first()
        if orm is None:
            orm = UserStateModel(user_id=user_id, **{f: getattr(state, f) for f in _FIELDS})
            self._session.add(orm)
        else:
            for field in _FIELDS:
                setattr(orm, field, getattr(state, field))
        self._session.flush()
        self._session.refresh(orm)
        return self._to_domain(orm)

    def delete_by_user(self, user_id: int) -> int:
        orm = self._session.scalars(
            select(UserStateModel).where(UserStateModel.user_id == user_id)
        ).first()
        if orm is None:
            return 0
        self._session.delete(orm)
        self._session.flush()
        return 1

    @staticmethod
    def _to_domain(orm: UserStateModel) -> UserStateData:
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


__all__ = ["UserStateRepository"]
