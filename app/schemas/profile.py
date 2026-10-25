"""User-portrait API schemas.

The static portrait and the adaptive state it seeds. The numeric compatibility
fields are cold-start projections, overridden by observed feedback as
``update_count`` grows - they must never be presented as a psychological
diagnosis.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProfileRead(BaseModel):
    """Static portrait plus the adaptive state it seeds."""

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
    "ModelRuntimeRead",
    "ProfileRead",
]


class ModelRuntimeRead(BaseModel):
    """``GET /users/me/model-runtime`` - versions, modes and shadow summary."""

    requested_mode: str
    effective_mode: str
    mode_reason: str | None = None
    layers: list[dict] = Field(default_factory=list)
    shadow_summary: dict = Field(default_factory=dict)
