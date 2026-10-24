"""Level 3 Progressive Execution Predictor V1."""
from __future__ import annotations

import uuid

from .config import Level3Config
from .features import build_features, compute_history_ratio_median, smoothed_completion
from .schemas import (
    Level3PredictionInput,
    Level3PredictionResult,
    OutcomeRecord,
    PredictionSnapshot,
)


class Level3Predictor:
    def __init__(self, config: Level3Config | None = None):
        self.config = config or Level3Config()
        self._snapshots: dict[str, PredictionSnapshot] = {}
        self._outcomes: list[OutcomeRecord] = []
        self._learned = {"completion_model": None, "duration_model": None, "eligible": False, "reasons": []}

    def create_snapshot(self, inp: Level3PredictionInput) -> PredictionSnapshot:
        features = build_features(inp)
        sid = str(uuid.uuid4())
        snap = PredictionSnapshot(
            snapshot_id=sid,
            prediction_timestamp=inp.context.prediction_timestamp,
            trait=inp.trait,
            state=inp.state,  # pre-task S_d^-
            task=inp.task,
            context=inp.context,
            history=inp.history,
            feature_snapshot=features,
        )
        self._snapshots[sid] = snap
        return snap

    def predict(self, inp: Level3PredictionInput) -> Level3PredictionResult:
        snap = self.create_snapshot(inp)
        features = snap.feature_snapshot
        h = inp.history
        support = h.support

        # Check eligibility for learned model
        if self._learned["eligible"] and self._learned["completion_model"] is not None:
            try:
                res = self._predict_learned(inp, snap, features)
                if res is not None:
                    return res
            except Exception:
                # fallback
                pass

        # History baseline
        if support.total_historical_tasks >= self.config.min_history_for_baseline and (support.usable_duration_samples >= 1 or h.duration_ratio_history):
            res = self._predict_history_baseline(inp, snap, features)
            if res is not None:
                return res

        # Cold start
        return self._predict_cold_start(inp, snap, features)

    def _predict_cold_start(self, inp, snap, features):
        # Duration = estimated_duration (baseline)
        pred_dur = float(inp.task.estimated_duration_minutes)
        return Level3PredictionResult(
            completion_probability=None,
            completion_uncertainty=None,
            completion_interval=None,
            predicted_duration_minutes=pred_dur,
            duration_uncertainty=None,
            duration_interval=None,
            prediction_mode="cold_start",
            prediction_status="insufficient_behavior_data",
            model_version=self.config.model_version,
            prediction_timestamp=inp.context.prediction_timestamp,
            data_support=inp.history.support,
            feature_snapshot_id=snap.snapshot_id,
            source_level1_version=inp.trait.model_version,
            source_level2_version=inp.state.model_version,
            reasons=["No sufficient real historical data; completion probability not fabricated."],
            feature_vector=features,
        )

    def _predict_history_baseline(self, inp, snap, features):
        support = inp.history.support
        med_ratio, ratio_source = compute_history_ratio_median(inp)
        if med_ratio is None or med_ratio <= 0:
            med_ratio = 1.0
            ratio_source = "fallback_to_estimated"

        pred_dur = float(inp.task.estimated_duration_minutes) * float(med_ratio)
        # avoid negative
        if pred_dur < 0:
            pred_dur = float(inp.task.estimated_duration_minutes)

        p_comp, p_unc = smoothed_completion(inp, self.config.beta_binomial_prior_alpha, self.config.beta_binomial_prior_beta)
        if p_comp is None:
            p_comp = None
            p_unc = None
        else:
            # clamp
            p_comp = max(0.0, min(1.0, p_comp))
            if p_unc is not None:
                lo = max(0.0, p_comp - 1.96 * p_unc)
                hi = min(1.0, p_comp + 1.96 * p_unc)
                comp_interval = (lo, hi)
            else:
                comp_interval = None
        status = "ok" if p_comp is not None else "insufficient_behavior_data"
        return Level3PredictionResult(
            completion_probability=p_comp,
            completion_uncertainty=p_unc,
            completion_interval=comp_interval if p_comp is not None else None,
            predicted_duration_minutes=pred_dur,
            duration_uncertainty=None,
            duration_interval=None,
            prediction_mode="history_baseline",
            prediction_status=status,
            model_version=self.config.model_version,
            prediction_timestamp=inp.context.prediction_timestamp,
            data_support=support,
            feature_snapshot_id=snap.snapshot_id,
            source_level1_version=inp.trait.model_version,
            source_level2_version=inp.state.model_version,
            reasons=[f"Duration baseline: {ratio_source} (median ratio)"],
            feature_vector=features,
        )

    def _predict_learned(self, inp, snap, features):
        # Framework only - returns None if not properly fitted
        return None

    def record_outcome(self, outcome: OutcomeRecord) -> None:
        self._outcomes.append(outcome)

    def check_learned_eligibility(self) -> dict:
        # Check data
        completed = sum(1 for o in self._outcomes if o.completed)
        failed = sum(1 for o in self._outcomes if not o.completed)
        duration_ok = sum(1 for o in self._outcomes if o.actual_duration_minutes is not None and o.completed)
        reasons = []
        eligible = True
        if len(self._outcomes) < self.config.min_history_tasks_for_learned:
            eligible = False
            reasons.append(f"insufficient_samples:{len(self._outcomes)}<{self.config.min_history_tasks_for_learned}")
        if completed < self.config.min_completed_and_failed or failed < self.config.min_completed_and_failed:
            eligible = False
            reasons.append("need_both_classes")
        if duration_ok < self.config.min_duration_samples:
            reasons.append(f"few_duration_samples:{duration_ok}")
        self._learned["eligible"] = eligible
        self._learned["reasons"] = reasons
        return {"learned_model_eligible": eligible, "reasons": reasons, "outcome_count": len(self._outcomes)}

    def ablation_evaluate(self) -> dict:
        # Framework for ablation when data available
        return {
            "models": ["A:Task+Context+History", "B:+Trait", "C:+Trait+State"],
            "completion_metrics": {"A": {}, "B": {}, "C": {}},
            "duration_metrics": {"A": {}, "B": {}, "C": {}},
            "note": "Run with real data to compute metrics; synthetic data only for implementation validation."
        }
