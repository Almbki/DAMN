"""Central configuration for DDSR-V1.

Every tunable value lives here.  ``parameter_sources`` makes the distinction
between literature-supported design choices and engineering initializations
explicit; V1 has no learned/personalized parameters (personalization is off).
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

STATE_KEYS: tuple[str, ...] = ("fatigue", "stress", "self_efficacy")

ALLOWED_SOURCE_CATEGORIES: frozenset[str] = frozenset(
    {
        "literature_supported_design_choice",
        "engineering_initialization",
        "learned_or_personalized",
    }
)

#: One entry per tunable parameter.  ``note`` is intentionally explicit about
#: what the cited paper does and does not provide.
PARAMETER_SOURCES: dict[str, dict[str, str]] = {
    "state_scale": {
        "category": "engineering_initialization",
        "note": (
            "All three states are mapped to 0-1 for a common grid. The papers use "
            "different published scales (1-5, 1-9, 1-6); those scales are not "
            "copied or treated as interchangeable."
        ),
    },
    "state_set": {
        "category": "literature_supported_design_choice",
        "note": (
            "Fatigue and stress as daily states follow Åkerstedt et al. (2014); "
            "daily self-efficacy follows Bellhäuser et al. (2023) and the "
            "self-efficacy/goal-attainment loop in Wäschle et al. (2014)."
        ),
    },
    "nightly_reflection": {
        "category": "literature_supported_design_choice",
        "note": (
            "A single evening reconstruction is supported by Kahneman et al. "
            "(2004, DRM) and by the evening diary in Bellhäuser et al. (2023)."
        ),
    },
    "behavior_state_separation": {
        "category": "literature_supported_design_choice",
        "note": (
            "Behavioral indicators are kept separate from states. Loeffler et al. "
            "(2019) show that behavioural delay alone cannot identify "
            "procrastination and that reasons must be assessed."
        ),
    },
    "self_efficacy_goal_attainment_direction": {
        "category": "literature_supported_design_choice",
        "note": (
            "Wäschle et al. (2014) report reciprocal positive relations between "
            "self-efficacy and perceived goal achievement. Only the direction is "
            "inherited; no coefficient is transferred."
        ),
    },
    "fatigue_stress_daily_states": {
        "category": "literature_supported_design_choice",
        "note": (
            "Åkerstedt et al. (2014) measured fatigue daily and stress several "
            "times per day across 42 days and found day-level associations. No "
            "daily transition coefficient is taken from that paper."
        ),
    },
    "procrastination_definition": {
        "category": "literature_supported_design_choice",
        "note": (
            "Procrastination requires voluntary delay/avoidance. External "
            "interruption, illness, task difficulty, and plan change are excluded "
            "by schema validation."
        ),
    },
    "persistence_autoregression": {
        "category": "literature_supported_design_choice",
        "note": (
            "Day-to-day persistence is consistent with the autoregressive / "
            "lagged designs in Bellhäuser et al. (2023), Wäschle et al. (2014), "
            "and Åkerstedt et al. (2014). The numeric rho is not from them."
        ),
    },
    "grid_min": {
        "category": "engineering_initialization",
        "note": "Numerical grid lower bound for the 0-1 state scale.",
    },
    "grid_max": {
        "category": "engineering_initialization",
        "note": "Numerical grid upper bound for the 0-1 state scale.",
    },
    "grid_n": {
        "category": "engineering_initialization",
        "note": "Numerical grid resolution (101 points).",
    },
    "cold_start_mean": {
        "category": "engineering_initialization",
        "note": (
            "Transparent neutral population prior at 0.5 on the 0-1 scale. It is "
            "not an individualized estimate and is not derived from the papers."
        ),
    },
    "cold_start_sd": {
        "category": "engineering_initialization",
        "note": "Transparent cold-start uncertainty (0.25 on the 0-1 scale).",
    },
    "persistence_rho": {
        "category": "engineering_initialization",
        "note": (
            "AR(1) persistence value 0.6. The design is literature-consistent, "
            "but this exact value is an engineering initialization, not estimated."
        ),
    },
    "process_noise_sd": {
        "category": "engineering_initialization",
        "note": (
            "Day-to-day process noise 0.12. It prevents uncertainty collapse and "
            "state lock; it is not a published coefficient."
        ),
    },
    "evidence_sharpness": {
        "category": "engineering_initialization",
        "note": (
            "Likelihood tilt per unit evidence strength (2.0). It controls how far "
            "one explicit statement can move a state."
        ),
    },
    "strength_weights": {
        "category": "engineering_initialization",
        "note": (
            "Mapping from weak/moderate/strong evidence to numeric strength "
            "(0.35/0.65/1.0)."
        ),
    },
    "goal_attainment_weight": {
        "category": "engineering_initialization",
        "note": (
            "Weight of the task-log goal-attainment signal on self-efficacy (0.6). "
            "The direction is supported by Wäschle et al. (2014); the magnitude is "
            "an engineering choice."
        ),
    },
    "uncertainty_floor": {
        "category": "engineering_initialization",
        "note": "Posterior SD floor (0.02) to avoid overconfident point states.",
    },
    "uncertainty_ceiling": {
        "category": "engineering_initialization",
        "note": "Prior/posterior SD ceiling (0.50) to avoid uncertainty explosion.",
    },
    "late_start_candidate_minutes": {
        "category": "engineering_initialization",
        "note": (
            "A start delay of at least 60 minutes is recorded only as a candidate "
            "for review; it is never labelled procrastination by itself."
        ),
    },
    "min_quote_chars": {
        "category": "engineering_initialization",
        "note": "Minimum audit quote length (2 characters).",
    },
    "conflict_policy": {
        "category": "engineering_initialization",
        "note": (
            "Opposing evidence is combined by symmetric Bayesian likelihood "
            "multiplication; conflicts are flagged, not silently discarded."
        ),
    },
    "extraction_failure_policy": {
        "category": "engineering_initialization",
        "note": (
            "Fail closed: an invalid LLM extraction contributes no evidence and is "
            "recorded as an error; the day still completes with higher uncertainty."
        ),
    },
    "passive_context_enabled": {
        "category": "engineering_initialization",
        "note": (
            "V1 never reads passive context. The interface exists only for future "
            "wearable/phone data."
        ),
    },
    "personalization_enabled": {
        "category": "learned_or_personalized",
        "note": (
            "V1 does not learn personalized transition parameters. Prediction "
            "errors are stored as future training data, not used for online "
            "learning."
        ),
    },
}


@dataclass(frozen=True)
class DDSRConfig:
    config_version: str = "ddsr_v1_config_1"
    grid_min: float = 0.0
    grid_max: float = 1.0
    grid_n: int = 101
    cold_start_mean: dict[str, float] = field(
        default_factory=lambda: {"fatigue": 0.5, "stress": 0.5, "self_efficacy": 0.5}
    )
    cold_start_sd: float = 0.25
    persistence_rho: dict[str, float] = field(
        default_factory=lambda: {"fatigue": 0.6, "stress": 0.6, "self_efficacy": 0.6}
    )
    process_noise_sd: dict[str, float] = field(
        default_factory=lambda: {"fatigue": 0.12, "stress": 0.12, "self_efficacy": 0.12}
    )
    evidence_sharpness: float = 2.0
    strength_weights: dict[str, float] = field(
        default_factory=lambda: {"weak": 0.35, "moderate": 0.65, "strong": 1.0}
    )
    goal_attainment_weight: float = 0.6
    uncertainty_floor: float = 0.02
    uncertainty_ceiling: float = 0.50
    late_start_candidate_minutes: int = 60
    min_quote_chars: int = 2
    conflict_policy: str = "symmetric_bayes_product"
    extraction_failure_policy: str = "fail_closed"
    passive_context_enabled: bool = False
    personalization_enabled: bool = False
    parameter_sources: dict[str, dict[str, str]] = field(
        default_factory=lambda: copy.deepcopy(PARAMETER_SOURCES)
    )

    def __post_init__(self) -> None:
        if not (0.0 <= self.grid_min < self.grid_max <= 1.0):
            raise ValueError("grid must satisfy 0 <= min < max <= 1")
        if self.grid_n < 11:
            raise ValueError("grid_n must be at least 11")
        for key in STATE_KEYS:
            if key not in self.cold_start_mean:
                raise ValueError(f"cold_start_mean missing {key}")
            if not (0.0 < self.persistence_rho[key] < 1.0):
                raise ValueError(f"persistence_rho[{key}] must be in (0, 1)")
            if self.process_noise_sd[key] < 0:
                raise ValueError(f"process_noise_sd[{key}] must be >= 0")
        if self.cold_start_sd <= 0:
            raise ValueError("cold_start_sd must be > 0")
        if not (0.0 < self.uncertainty_floor < self.uncertainty_ceiling):
            raise ValueError("uncertainty_floor must be below uncertainty_ceiling")
        if self.evidence_sharpness <= 0:
            raise ValueError("evidence_sharpness must be > 0")
        if self.goal_attainment_weight < 0:
            raise ValueError("goal_attainment_weight must be >= 0")
        for name in self.parameter_sources:
            category = self.parameter_sources[name].get("category")
            if category not in ALLOWED_SOURCE_CATEGORIES:
                raise ValueError(
                    f"parameter {name!r} has invalid source category {category!r}"
                )
        missing = [
            name
            for name in (
                "state_scale",
                "state_set",
                "nightly_reflection",
                "behavior_state_separation",
                "self_efficacy_goal_attainment_direction",
                "fatigue_stress_daily_states",
                "procrastination_definition",
                "persistence_autoregression",
                "grid_min",
                "grid_max",
                "grid_n",
                "cold_start_mean",
                "cold_start_sd",
                "persistence_rho",
                "process_noise_sd",
                "evidence_sharpness",
                "strength_weights",
                "goal_attainment_weight",
                "uncertainty_floor",
                "uncertainty_ceiling",
                "late_start_candidate_minutes",
                "min_quote_chars",
                "conflict_policy",
                "extraction_failure_policy",
                "passive_context_enabled",
                "personalization_enabled",
            )
            if name not in self.parameter_sources
        ]
        if missing:
            raise ValueError(f"missing parameter provenance: {missing}")

    @property
    def grid(self) -> list[float]:
        if self.grid_n == 1:
            return [self.grid_min]
        step = (self.grid_max - self.grid_min) / (self.grid_n - 1)
        return [self.grid_min + i * step for i in range(self.grid_n)]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DDSRConfig:
        known = {field_name for field_name in cls.__dataclass_fields__}
        payload = {key: value for key, value in data.items() if key in known}
        if "parameter_sources" not in payload:
            payload["parameter_sources"] = copy.deepcopy(PARAMETER_SOURCES)
        return cls(**payload)

    @classmethod
    def from_json(cls, path: str | Path | None = None) -> DDSRConfig:
        path = Path(path) if path is not None else CONFIG_PATH
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


def load_config(path: str | Path | None = None) -> DDSRConfig:
    return DDSRConfig.from_json(path)
