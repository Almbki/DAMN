"""Level 3 configuration with parameter provenance."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Level3Config:
    config_version: str = "level3_v1_config_1"
    model_version: str = "level3_v1"

    # Eligibility for learned model
    min_history_tasks_for_learned: int = 30
    min_completed_and_failed: int = 5
    min_feature_coverage: float = 0.6
    min_duration_samples: int = 10
    require_probability_calibration_ok: bool = True

    # History baseline
    min_history_for_baseline: int = 3
    min_similar_for_similar_baseline: int = 2
    beta_binomial_prior_alpha: float = 1.0  # engineering initialization
    beta_binomial_prior_beta: float = 1.0   # engineering initialization

    # Regularization
    ridge_alpha: float = 1.0  # engineering initialization
    logistic_C: float = 1.0   # engineering initialization

    # Uncertainty
    uncertainty_floor: float = 0.01
    uncertainty_ceiling: float = 0.99

    # Leakage guards
    forbid_post_task_features: bool = True

    parameter_sources: dict = field(default_factory=lambda: {
        "min_history_tasks_for_learned": {"category": "engineering_initialization", "note": "Gate threshold; not from a specific paper."},
        "min_completed_and_failed": {"category": "engineering_initialization", "note": "Need both classes for classification."},
        "beta_binomial_prior_alpha": {"category": "engineering_initialization", "note": "Uniform prior for smoothing; not paper-estimated."},
        "beta_binomial_prior_beta": {"category": "engineering_initialization", "note": "Uniform prior for smoothing; not paper-estimated."},
        "ridge_alpha": {"category": "engineering_initialization", "note": "Weak regularization default for small data."},
        "logistic_C": {"category": "engineering_initialization", "note": "Inverse regularization; engineering default."},
        "duration_log_transform": {"category": "literature_supported_design_choice", "note": "Log ratio reduces skew / planning fallacy effects (Buehler et al.)."},
        "beta_binomial_smoothed_completion": {"category": "literature_supported_design_choice", "note": "Conservative smoothing for small samples."},
        "history_baseline_median_ratio": {"category": "literature_supported_design_choice", "note": "Robust to outliers; aligns with experience-based correction."},
    })
