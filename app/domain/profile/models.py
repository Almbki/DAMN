"""Profile data contracts (persistence/display only).

The old EWMA engine was a second, competing source of dynamic state. It has
been removed; traits come from ``app.user_models.level1`` and dynamic state from
``app.user_models.level2``. This package now only holds the dataclasses used by
repositories and the compatibility API.

``UserStateData`` is a *view*: ``level2_profile`` is the source of truth and the
legacy float fields are projections that keep the existing wire contract stable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class UserProfileData:
    """Static self-reported profile."""

    identity: str | None = None


@dataclass(frozen=True, slots=True)
class UserStateData:
    """Persistence/display view of the Level 2 dynamic state."""

    duration_factor: float = 1.3
    completion_prob: float = 0.7
    stress_baseline: float = 0.5
    energy_drain_rate: float = 0.5
    proactive_score: float = 0.5
    procrastination_tendency: float = 0.5
    preferred_time_slots: dict[str, str] = field(default_factory=dict)
    stress_response: float = 0.5
    state_energy: float = 0.5
    state_fatigue: float = 0.5
    self_efficacy: float = 0.5
    update_count: int = 0
    # --- Level 2 real dynamic state (DDSR-V1) -----------------------------
    state_stress: float = 0.5
    state_fatigue_uncertainty: float = 0.25
    state_stress_uncertainty: float = 0.25
    self_efficacy_uncertainty: float = 0.25
    #: The auditable Level 2 profile JSON; the source of truth for state.
    level2_profile: dict[str, Any] | None = None
    level2_profile_date: date | None = None
    level2_model_version: str | None = None
    level2_config_version: str | None = None
    level2_artifact_hash: str | None = None
    level2_updated_at: datetime | None = None

    def is_degraded(self) -> bool:
        """True until a real Level 2 profile with enough history exists."""
        return self.level2_profile is None or self.update_count < 3


__all__ = ["UserProfileData", "UserStateData"]