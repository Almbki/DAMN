"""Feature engineering with anti-leakage."""
from __future__ import annotations

import math

from .schemas import Level3PredictionInput


def build_features(inp: Level3PredictionInput) -> dict:
    t = inp.task
    s = inp.state
    c = inp.context
    h = inp.history

    hours_to_deadline = None
    if t.deadline is not None:
        delta = (t.deadline - c.prediction_timestamp).total_seconds() / 3600.0
        hours_to_deadline = delta

    features = {
        # Trait
        "trait_n": inp.trait.theta_n,
        "trait_e": inp.trait.theta_e,
        "trait_o": inp.trait.theta_o,
        "trait_a": inp.trait.theta_a,
        "trait_c": inp.trait.theta_c,
        "trait_n_se": inp.trait.se_n,
        "trait_e_se": inp.trait.se_e,
        "trait_o_se": inp.trait.se_o,
        "trait_a_se": inp.trait.se_a,
        "trait_c_se": inp.trait.se_c,
        # State (pre-task S_d^-)
        "state_fatigue": s.fatigue,
        "state_fatigue_unc": s.fatigue_uncertainty,
        "state_stress": s.stress,
        "state_stress_unc": s.stress_uncertainty,
        "state_self_efficacy": s.self_efficacy,
        "state_self_efficacy_unc": s.self_efficacy_uncertainty,
        # Task
        "task_estimated_duration": t.estimated_duration_minutes,
        "task_difficulty": t.difficulty,
        "hours_to_deadline": hours_to_deadline,
        "has_planned_start": 1.0 if t.has_planned_start else 0.0,
        "task_type": t.task_type,
        # Context
        "time_of_day": c.time_of_day,
        "available_time_minutes": c.available_time_minutes,
        # History
        "hist_total": h.support.total_historical_tasks,
        "hist_completed": h.support.completed_task_count,
        "hist_failed": h.support.failed_task_count,
        "hist_usable_duration": h.support.usable_duration_samples,
        "hist_similar_count": h.support.similar_task_sample_count,
        "hist_recent_goal_attainment": h.recent_goal_attainment,
    }
    return features


def compute_history_ratio_median(h: Level3PredictionInput) -> tuple[float | None, str]:
    ratios = [r for r in h.history.duration_ratio_history if r is not None and r > 0]
    if h.history.similar_duration_ratio_history and h.history.support.similar_task_sample_count >= 2:
        srat = [r for r in h.history.similar_duration_ratio_history if r is not None and r > 0]
        if srat:
            srat_sorted = sorted(srat)
            med = srat_sorted[len(srat_sorted) // 2]
            return med, "similar_task_median"
    if ratios:
        ratios_sorted = sorted(ratios)
        med = ratios_sorted[len(ratios_sorted) // 2]
        return med, "global_user_median"
    return None, "none"


def smoothed_completion(h: Level3PredictionInput, alpha: float = 1.0, beta: float = 1.0) -> tuple[float | None, float | None]:
    hist = h.history.completion_history
    if not hist:
        return None, None
    k = sum(1 for x in hist if x)
    n = len(hist)
    p = (k + alpha) / (n + alpha + beta)
    # simple uncertainty proxy
    var = (k + alpha) * (n - k + beta) / ((n + alpha + beta) ** 2 * (n + alpha + beta + 1))
    unc = math.sqrt(max(var, 1e-12))
    return p, unc
