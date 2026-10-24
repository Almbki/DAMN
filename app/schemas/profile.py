"""User-portrait API schemas.

MBTI is a SOFT self-report input. The numeric fields are cold-start priors
derived from it and are overridden by observed feedback as ``update_count``
grows - they must never be presented as a psychological diagnosis.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

#: The four MBTI dimension keys accepted in ``mbti_dims``.
MBTI_DIMENSION_KEYS: frozenset[str] = frozenset({"ie", "sn", "tf", "jp"})


def normalise_mbti_type(value: str | None) -> str | None:
    """Uppercase/validate a 4-letter MBTI code (``None`` stays ``None``)."""
    if value is None:
        return None
    cleaned = value.strip().upper()
    if not cleaned:
        return None
    if len(cleaned) != 4 or not cleaned.isalpha():
        raise ValueError("mbti_type must be 4 letters, e.g. INTP")
    return cleaned


def validate_mbti_dims(value: dict[str, float] | None) -> dict[str, float] | None:
    """Reject unknown dimension keys and clamp each weight to [0, 1]."""
    if value is None:
        return None
    unknown = set(value) - MBTI_DIMENSION_KEYS
    if unknown:
        raise ValueError(f"unknown mbti_dims keys: {sorted(unknown)}")
    return {key: max(0.0, min(1.0, float(weight))) for key, weight in value.items()}


class ProfileRead(BaseModel):
    """Static portrait plus the adaptive state it seeds."""

    mbti_type: str | None = None
    mbti_dims: dict[str, float] | None = None
    identity: str | None = None
    # --- adaptive state (EWMA-updated by feedback) ---
    duration_factor: float
    completion_prob: float
    stress_baseline: float
    energy_drain_rate: float
    proactive_score: float
    procrastination_tendency: float
    preferred_time_slots: dict[str, str] = Field(default_factory=dict)
    stress_response: float
    state_energy: float
    state_fatigue: float
    #: Level 2 stress projection (0..1). Null-safe legacy field.
    state_stress: float = 0.5
    self_efficacy: float
    update_count: int = 0
    #: True while ``update_count < 3`` - predictions are cold-start priors.
    degraded: bool = True
    # --- real three-layer model snapshots (additive, authoritative) --------
    #: Level 1 TraitSnapshotV1 JSON (N/E/O/A/C theta + SE + metadata).
    trait: dict | None = None
    #: Level 2 DynamicStateSnapshot JSON (pre-task state + metadata).
    state: dict | None = None
    #: Artifact/version metadata for Level 1/2/3.
    model_metadata: list[dict] = Field(default_factory=list)

    @classmethod
    def from_parts(
        cls, profile, state, *, trait: dict | None = None, level2: dict | None = None,
        model_metadata: list[dict] | None = None,
    ) -> ProfileRead:
        return cls(
            mbti_type=profile.mbti_type,
            mbti_dims=dict(profile.mbti_dims) if profile.mbti_dims else None,
            identity=profile.identity,
            duration_factor=state.duration_factor,
            completion_prob=state.completion_prob,
            stress_baseline=state.stress_baseline,
            energy_drain_rate=state.energy_drain_rate,
            proactive_score=state.proactive_score,
            procrastination_tendency=state.procrastination_tendency,
            preferred_time_slots=dict(state.preferred_time_slots),
            stress_response=state.stress_response,
            state_energy=state.state_energy,
            state_fatigue=state.state_fatigue,
            state_stress=state.state_stress,
            self_efficacy=state.self_efficacy,
            update_count=state.update_count,
            degraded=state.is_degraded(),
            trait=trait,
            state=level2,
            model_metadata=list(model_metadata or []),
        )


__all__ = [
    "MBTI_DIMENSION_KEYS",
    "ModelRuntimeRead",
    "ProfileRead",
    "normalise_mbti_type",
    "validate_mbti_dims",
]


class ModelRuntimeRead(BaseModel):
    """``GET /users/me/model-runtime`` - versions, modes and shadow summary."""

    requested_mode: str
    effective_mode: str
    mode_reason: str | None = None
    layers: list[dict] = Field(default_factory=list)
    shadow_summary: dict = Field(default_factory=dict)
