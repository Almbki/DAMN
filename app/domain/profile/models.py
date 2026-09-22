"""User-profile domain dataclasses (stdlib only - no FastAPI/SQLAlchemy).

Mirrors ``ideas and structures/Prompts/画像.md`` §1: static profile + dynamic
state, per ``docs/fin/核心闭环.md`` 环节 1. All dynamic fields are plain Python
floats in [0, 1] (except ``duration_factor`` which is a unitless multiplier and
``update_count``).

Every dataclass is frozen: ``update_state`` returns a brand-new
``UserStateData`` via ``dataclasses.replace`` and never mutates its input.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class UserProfileData:
    """Static per-user portrait from registration / questionnaire.

    ``mbti_dims`` holds a subset of the ``ie``/``sn``/``tf``/``jp`` keys with
    weights in [0, 1]; each weight is the pull toward the FIRST letter of the
    matching ``DIMENSION_LETTERS`` pair (e.g. ``ie=0.65`` means 65% I, 35% E).
    """

    mbti_type: str | None = None
    mbti_dims: dict[str, float] | None = None
    identity: str | None = None


@dataclass(frozen=True, slots=True)
class UserStateData:
    """Dynamic, feedback-updated state (EWMA) of the user model.

    Fields 2-8 are seeded from the MBTI template at registration; the rest
    start at template-neutral 0.5 and are updated by ``engine.update_state``.
    """

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

    def is_degraded(self) -> bool:
        """Fewer than 3 feedback updates: predictions are cold-start degraded."""
        return self.update_count < 3


@dataclass(frozen=True, slots=True)
class DurationEstimate:
    """Duration point estimate plus degradation flag."""

    q50: float
    q80: float
    degraded: bool


@dataclass(frozen=True, slots=True)
class CompletionEstimate:
    """Completion-probability estimate plus degradation flag."""

    prob: float
    degraded: bool


@dataclass(frozen=True, slots=True)
class ReplanDecision:
    """Replan verdict (画像.md §4)."""

    decision: str
    reason_code: str
