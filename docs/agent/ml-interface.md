# ML Interface

The agent **consumes** predictions; it never trains or implements a model.

Code: `app/ml/` (interfaces + fallbacks), consumed through the
`task_duration_predictor` tool and `nodes/prediction.py`.

## Two groups of interfaces

### 1. Per-task predictors (unchanged by this refactor)

```python
class DurationPredictor(Protocol):
    name: str
    def predict(self, request: PredictionRequest) -> DurationPrediction: ...
```

| Protocol | Returns | Used by |
| --- | --- | --- |
| `DurationPredictor` | `DurationPrediction{theoretical_minutes, predicted_minutes, factor, confidence, source}` | `user_situation_analysis`, `plan_generation` |
| `CompletionPredictor` | `CompletionPrediction{probability, confidence, source}` | same |
| `StressPredictor` | `StressPrediction{predicted_stress, predicted_load_level, should_reduce_load, confidence, source}` | same |
| `TimeSlotPredictor` | `TimeSlotPrediction{recommended_slot, alternatives, confidence, source}` | same |

Input: `PredictionRequest{task: TaskFeatureSet, user: UserFeatureSet, time_of_day, available_minutes}`.

### 2. Adjustment predictor (new — drives the feedback router)

```python
class AdjustmentPredictor(Protocol):
    name: str
    def predict_adjustment(self, request: AdjustmentRequest) -> AdjustmentPrediction: ...
```

`AdjustmentPrediction`:

| Field | Type | Meaning |
| --- | --- | --- |
| `route` | `AdjustmentRoute` | `NO_CHANGE` / `MICRO_ADJUST` / `FULL_REPLAN` |
| `severity` | `AdjustmentSeverity` | `NONE` / `LOW` / `MEDIUM` / `HIGH` |
| `confidence` | float 0..1 | model confidence |
| `predicted_parameters` | `dict[str, float]` | e.g. `suggested_daily_limit_factor` — consumed by `micro_adjustment` |
| `reasons` | `list[str]` | surfaced in the API response and the trace |
| `recommended_action` | `str \| None` | human-readable hint |
| `source` | str | **must be truthful**: `llm` / `xgboost-v1` / `fallback:rule` / `mock` |

`AdjustmentRequest` carries: `user: UserFeatureSet`, `progress: PlanProgress`,
`recent_feedback: list[FeedbackSignal]`, `task_features: list[TaskFeatureSet]`,
`current_daily_load_minutes`, `available_minutes_per_day`, `user_note`.

## Bundling — `app/ml/predictors.py`

```python
class PredictorSet:
    duration, completion, stress, time_slot, adjustment
    @classmethod default(cls) -> PredictorSet
```

`PlanService(predictors=...)` is the only injection point. Replace any member
without touching the graph, nodes, prompts or API:

```python
predictors = PredictorSet(
    duration=LgbmDurationPredictor.load("models/duration.txt"),
    completion=CalibratedCompletionPredictor.load("models/completion.txt"),
    stress=PredictorSet.default().stress,
    time_slot=BayesianTimeSlotPredictor(),
    adjustment=XgbAdjustmentPredictor.load("models/adjustment.txt"),
)
PlanService(session, predictors=predictors)
```

## Fallbacks that ship today

| Implementation | `source` | Behaviour |
| --- | --- | --- |
| `StatisticalDurationPredictor` | `mock:statistical` | `theoretical × duration_factor` (+15 % high load, difficulty nudge) |
| `StatisticalCompletionPredictor` | `mock:statistical` | 7d/30d completion blend with energy/stress/duration penalties |
| `StatisticalStressPredictor` | `mock:statistical` | `avg_stress + load delta`, flags `should_reduce_load` |
| `StatisticalTimeSlotPredictor` | `mock:statistical` | user preference lookup, else a static default map |
| `RuleBasedAdjustmentPredictor` | **`fallback:rule`** | deterministic route from recent completion / stress / energy |
| `MockAdjustmentPredictor` | `mock` | test double with a caller-fixed route |

The rule-based adjustment predictor exists so the loop runs before the ML model
is delivered: no feedback → `NO_CHANGE`; 7-day average ≥ 0.8 with calm
stress/energy → `NO_CHANGE`; ≥ 0.5 → `MICRO_ADJUST`; below → `FULL_REPLAN`.
It is **not** machine learning and never claims to be.

## ML never decides alone

`AdjustmentRouter.decide()` takes the prediction as the primary signal but may
override it (no current plan, explicit user requirement, persistently failing
plan, too many micro adjustments). The ML team therefore owns *the estimate*;
the product owns *the policy*. See `docs/agent/state-machine.md`.

## Ready-to-train data

`task_executions` (planned vs actual, completion, stress before/after,
difficulty, time of day) joined with `tasks` (cognitive load, priority,
estimated/predicted duration), `goals` (deadline, subject) and `feedbacks`
(energy, sleep, completion). `user_models.sample_size` is the readiness signal
for switching a user from fallbacks to a trained model.
