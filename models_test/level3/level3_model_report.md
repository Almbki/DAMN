# Level 3 Model Report (V1)

## Overview
Level 3 is a supervised predictive layer for task execution outcomes. It predicts:
1. P(Complete | Trait, State, Task, Context, History)
2. E(ActualDuration | Trait, State, Task, Context, History)

Level 3 does **not** do scheduling, ordering/splitting/replanning, or LLM decision making.

## Inputs
- **Trait (Level 1, read-only)**: N/E/O/A/C theta + SE/uncertainty, model/version metadata
- **State (Level 2, read-only)**: pre-task S_d^- (fatigue/stress/self-efficacy + uncertainty). Post-task S_d^+ is never used.
- **Task**: task_id, estimated_duration, difficulty, deadline, planned_start (+ derived)
- **Context**: prediction_timestamp, time_of_day, available_time
- **History**: real TaskExecution history only; support counts tracked

## Progressive Prediction
- **MODE A - COLD START**: No sufficient history. `predicted_duration = estimated_duration`. `completion_probability = null`. `prediction_mode=cold_start`, `prediction_status=insufficient_behavior_data`.
- **MODE B - HISTORY BASELINE**: Smoothed empirical completion (Beta-Binomial with engineering priors) and robust median duration ratio (similar-task preferred if enough samples, else global). Conservative for small samples.
- **MODE C - LEARNED MODEL**: Regularized Logistic Regression (completion) and Ridge Regression on `log(actual/estimated)` (duration). Only enabled if eligibility gate passes; otherwise falls back to baseline.

## Anti-Leakage
- PredictionSnapshot frozen before outcome
- Only pre-task state used
- No future history
- No post-task information backfilled

## Eligibility Gate (Learned Model)
Checks: sample size, both classes present, feature coverage, leakage, validation, calibration, baseline comparison. If failed -> use History Baseline.

## Ablation Framework
A: Task+Context+History; B: +Trait; C: +Trait+State. Metrics: Brier, LogLoss, ROC-AUC (if valid), MAE, MedianAE, baseline-relative improvement. Real data decides gain/loss.

## Boundaries
- LLM not used for numeric prediction
- No synthetic accuracy claims
- Engineering initializations clearly marked
- Learned coefficients = NOT FITTED until real data
