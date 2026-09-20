# ML Layer

> **No trained model ships in v1.** `app/ml` provides Protocol interfaces plus
> clearly-marked *statistical* implementations (`name="statistical-*"`,
> `source="mock:statistical"`). They are replaceable without touching services
> or the API.

---

## 1. The prediction chain

```
理论工作量               用户实际数据              个体化预测               排期
theoretical_workload ─► task_executions/feedback ─► duration.predict ─┐
                        user_models (factors)      completion.predict ├─► Scheduler
                                                   stress.predict     │   (heuristic)
                                                   time_slot.predict ─┘
                                                          │
                                                          ▼
                                                   CandidateSchedule ─► RuleEngine
```

| Stage | Code |
| --- | --- |
| Theoretical workload | `app/agent/nodes/theoretical_analysis.py` (mock heuristic) |
| User history → features | `app/application/services/user_model_service.py` |
| Duration | `app/ml/duration_predictor.py` |
| Completion probability | `app/ml/completion_predictor.py` |
| Stress response | `app/ml/stress_predictor.py` |
| Recommended time slot | `app/ml/time_predictor.py` |
| User model factors | `app/ml/user_model.py` (`StatisticalUserModelBuilder`) |
| Scheduling | `app/domain/scheduling/scheduler.py` |

---

## 2. Contracts — `app/ml/base.py`

```python
class DurationPredictor(Protocol):
    name: str
    def predict(self, request: PredictionRequest) -> DurationPrediction: ...
```

| Protocol | Returns |
| --- | --- |
| `DurationPredictor` | `DurationPrediction{theoretical_minutes, predicted_minutes, factor, confidence, source}` |
| `CompletionPredictor` | `CompletionPrediction{probability, confidence, source}` |
| `StressPredictor` | `StressPrediction{predicted_stress, predicted_load_level, should_reduce_load, confidence, source}` |
| `TimeSlotPredictor` | `TimeSlotPrediction{recommended_slot, alternatives, confidence, source}` |

**Request** `PredictionRequest` = `TaskFeatureSet` + `UserFeatureSet` +
optional `time_of_day` / `available_minutes`.

| `TaskFeatureSet` | `UserFeatureSet` |
| --- | --- |
| `task_id` | `user_id` |
| `title`, `task_type`, `subject` | `duration_factor` |
| `estimated_duration_minutes` | `completion_rate_7d`, `completion_rate_30d` |
| `difficulty` (1..5) | `avg_stress`, `avg_energy` (0..10) |
| `cognitive_load`, `priority` | `sleep_hours`, `preferred_time_slots` |
| `deadline` | `sample_size`, `execution_weight` |

`PredictorSet.default()` bundles the four statistical implementations; services
depend only on the Protocols.

---

## 3. Feature source map (theory → measurable → DB column → feature)

| Feature | Source | DB column | Used by |
| --- | --- | --- | --- |
| theoretical workload | theoretical analysis agent | `tasks.estimated_duration` | DurationPredictor |
| cognitive load | task / keyword mapping | `tasks.cognitive_load` | all |
| difficulty | theoretical analysis | `tasks` (via draft) | DurationPredictor |
| planned duration | plan | `task_executions.planned_duration` | DurationPredictor training |
| actual duration | user execution | `task_executions.actual_duration` | duration factor |
| completion rate | user execution / feedback | `task_executions.completion_rate`, `feedbacks.completion_rate` | CompletionPredictor |
| stress before/after | self report | `task_executions.stress_before`, `stress_after` | StressPredictor |
| energy level | daily check-in | `feedbacks.energy_level` | CompletionPredictor |
| sleep hours | daily check-in | `feedbacks.sleep_hours` | CompletionPredictor, TimeSlotPredictor |
| time of day | execution context | `task_executions.time_of_day`, `feedbacks.dominant_time_of_day` | TimeSlotPredictor |
| failure / delay reason | user report | `task_executions.failure_reason`, `feedbacks.delay_reason` | analysis (not yet a feature) |
| deadline distance | goal | `goals.deadline` | CompletionPredictor (scheduling context) |

**Prediction targets** (matching the research plan):

- Model A — duration: `predicted_duration` ← task/user features
- Model B — completion: `P(completion)` ← difficulty, deadline distance, duration, stress, energy, recent completion
- Model C — stress: `predicted_stress` ← daily workload, high-cognitive minutes, recent completion, energy, sleep
- Model D — time slot: `recommended_time_slot` ← task type, time of day, historical performance

---

## 4. What the statistical mocks actually compute

| Predictor | Formula (v1) | Confidence |
| --- | --- | --- |
| `StatisticalDurationPredictor` | `predicted = round(estimated × factor)`; `factor = user.duration_factor`, `+0.15` if HIGH load, `+0.1×(difficulty−3)` if set, clamped `[0.6, 3.0]` | `min(0.35 + sample_size/50, 0.85)` |
| `StatisticalCompletionPredictor` | `base = 0.7×rate_7d + 0.3×rate_30d`; penalties: energy<4 `−0.15`, stress>7 `−0.15`, duration>available `−0.2`, HIGH load `−0.05`; clamp `[0.05, 0.98]` | `min(0.3 + sample_size/60, 0.8)` |
| `StatisticalStressPredictor` | `predicted = avg_stress + delta` (HIGH +2.0, MEDIUM +1.0, LOW 0, RESTORATIVE −1.0), clamp `[0, 10]`; `should_reduce_load = predicted ≥ 7 or (predicted − avg) ≥ 2` | `min(0.3 + sample_size/60, 0.8)` |
| `StatisticalTimeSlotPredictor` | preference lookup by `cognitive_load.value` then `task_type`, else `{high: morning, medium: morning, low: afternoon, restorative: evening}` | `0.7` if preference matched else `0.5` |

`StatisticalUserModelBuilder`:

- `build(executions, feedback, *, user_id, execution_weight, task_loads)` →
  per-load `duration_factors = mean(actual/planned)`, `completion_probability =
  mean(completion_rate)`, `stress_response = mean(stress_after − stress_before)`,
  `preferred_time_slots` = modal `time_of_day`, `sample_size = len(executions)`.
  Factors are blended toward `1.0` when the sample is small.
- `to_features(model, executions, feedback, *, user_id, execution_weight)` →
  `UserFeatureSet` with 7-day / 30-day completion rates, mean stress/energy,
  mean sleep, preferred slots, `sample_size`.

These are **statistics, not learning**. There is no training step, no
persistence of a fitted model, and no accuracy claim.

---

## 5. Data collection (what the app records)

`PATCH /plans/{plan_id}/tasks/{task_id}` with `completed = true` writes a
`TaskExecution` row:

- `planned_duration = predicted_duration or estimated_duration`
- `actual_duration`, `started_at`, `finished_at`
- `difficulty_feedback` (1..5), `stress_before` / `stress_after` (0..10)
- `failure_reason`

Daily check-ins (`POST /plans/{plan_id}/feedback`) add `completion_rate`,
`stress_level`, `energy_level`, `sleep_hours`, `delay_reason`, `dominant_time_of_day`.

`UserModelService.update_model(user_id)` recomputes `UserModel` from these rows.

---

## 6. Replacing the mocks with a real model

1. **Implement the Protocol** (example, LightGBM):

```python
# app/ml/duration_predictor.py  (or a new module, e.g. app/ml/lgbm_duration.py)
class LgbmDurationPredictor:
    name = "lightgbm-duration-v1"

    def __init__(self, booster) -> None:      # booster loaded by ModelStore
        self._booster = booster

    def predict(self, request: PredictionRequest) -> DurationPrediction:
        features = self._vectorize(request)   # TaskFeatureSet + UserFeatureSet
        minutes = int(self._booster.predict([features])[0])
        return DurationPrediction(
            theoretical_minutes=request.task.estimated_duration_minutes,
            predicted_minutes=minutes,
            factor=minutes / request.task.estimated_duration_minutes,
            confidence=0.8,
            source="lightgbm",
        )
```

2. **Load it** via `app/infrastructure/ml/model_store.py` (`ModelStore` Protocol;
   `FileModelStore` is a placeholder for exactly this use).
3. **Inject it**: `PlanService(session, predictors=PredictorSet(duration=..., ...))`
   or wire it in `deps.get_plan_service`. Nothing in `app/application` or
   `app/api` changes.
4. Keep `source` truthful so the API/insights can distinguish real models from mocks.

### Training data

Everything the four models need is already persisted: `task_executions`
(planned vs actual, stress deltas, difficulty, time of day) joined with
`tasks` (cognitive load, priority, estimated duration), `goals` (deadline,
type) and `feedbacks` (energy, sleep, completion). `sample_size` in `UserModel`
is the readiness signal for switching a user from statistical priors to a
trained model.

---

## 7. Honest limitations of v1

- No trained model, no training pipeline, no cross-user learning.
- `completion_probability` and `duration_factor` are per-user means, so they
  cannot capture task-type interactions or circadian effects yet.
- `time_slot` recommendations come from a static default map unless the user has
  history (`preferred_time_slots`).
- Confidence values are hand-set heuristics based on `sample_size`, not
  calibrated uncertainty.
- The Scheduler consumes predictions deterministically; it performs no
  optimisation over completion probability.
