# Three-Layer Model + Agent Integration (v1)

> Scope: integrating the real Level 1/2/3 user models into the main backend,
> running Level 3 in shadow mode, and converging the two historical LangGraph
> graphs into one planner runtime with explicit workflows.
>
> Status: implemented and verified on 2026-10-24. This document describes the
> code that exists now, not an intended future state.
>
> **V1.1 update:** auth/onboarding/demo/synthetic-scenario work is documented in
> [`认证与合成数据-v1.md`](认证与合成数据-v1.md). Current validation is
> **229 backend / 19 frontend** tests; §8 below is the historical V1 snapshot.

---

## 1. Final architecture

### 1.1 Directory (new/changed parts)

```text
app/
├─ user_models/                    # real model sidecar (no DB, no FastAPI)
│  ├─ contracts.py                 # typed snapshots, metadata, modes, history
│  ├─ artifacts.py                 # artifact hashing / version identity
│  ├─ errors.py                    # typed model errors
│  ├─ runtime.py                   # UserModelRuntime facade
│  ├─ shadow.py                    # Level3ShadowRunner + audit record
│  ├─ level1/
│  │  ├─ cat.py                    # copied frozen GRM/CAT implementation
│  │  ├─ runtime.py                # Level1Runtime + TraitProfileV1
│  │  └─ artifacts/                # grm_parameters / cat_config / item_mapping ...
│  ├─ level2/
│  │  ├─ ddsr/                     # copied frozen DDSR-V1 package + config.json
│  │  └─ runtime.py                # Level2Runtime (replay + typed snapshot)
│  └─ level3/
│     ├─ config.py / features.py / predictor.py / schemas.py / validation.py
│     └─ runtime.py                # Level3Runtime (inference only)
├─ application/
│  ├─ services/user_model_service.py  # DB -> Level2 replay -> shadow persist
│  ├─ services/profile_service.py     # Level1/2 access + compatibility view
│  ├─ services/model_runtime.py       # process-wide runtime factory
│  ├─ context/repo_context_builder.py # DB -> PlanningContext (incl. user_model)
│  └─ dto/{goal,situation,schedule_import}.py  # no app.schemas imports
├─ agent/
│  ├─ graph.py                     # PlannerRuntime + initial/replan workflows
│  ├─ features.py                  # TaskFeatureSet/UserFeatureSet/FeedbackSignal
│  ├─ nodes/adjustment_decision.py # deterministic policy node (replaces ML node)
│  ├─ tools/task_estimator.py      # deterministic production estimate
│  └─ retuned prompts (user_model / adjustment_decision)
├─ domain/
│  ├─ feedback/{models,adjustment,policy}.py  # pure route policy
│  ├─ scheduling/constants.py       # single DEFAULT_HORIZON_DAYS
│  └─ profile/models.py             # persistence/display view only
├─ infrastructure/database/
│  ├─ models/shadow_prediction.py
│  └─ repositories/shadow_prediction_repository.py
└─ alembic/versions/ffc6c69463aa_add_three_layer_user_model_runtime.py
```

Removed: `app/ml/**` (statistical mocks + adjustment predictor) and
`app/infrastructure/ml/model_store.py` (unused placeholder).

### 1.2 Dependency direction

```text
API (app/api, app/schemas)
  -> Application (app/application)
       -> Agent sidecar (app/agent)
       -> User-model sidecar (app/user_models)
       -> Domain (app/domain)
       -> Infrastructure (app/infrastructure/database, llm)
```

Verified by `tests/unit/test_architecture.py`:

* `app/domain` imports no FastAPI/SQLAlchemy/LangGraph and no outer layer.
* `app/agent` imports no SQLAlchemy and no database package.
* `app/application` imports no `app.schemas`.
* `app/user_models` imports no persistence, scheduler or rule engine.

---

## 2. The three models

| Layer | Role | Input | Output | Artifacts / version | Runtime caller |
| --- | --- | --- | --- | --- | --- |
| **Level 1** | Stable traits | IPIP-NEO-120 CAT responses | N/E/O/A/C `theta`, `se`, `ci95`, `items_answered` | `level1/artifacts/grm_parameters.json`, `cat_config.json`, `item_mapping.json`; `model_version=trait_v1`, `artifact_version=grm_v1` | `UserModelService.get_trait_profile` -> `Level1Runtime.snapshot`; `ProfileService.set_trait_profile` validates imports |
| **Level 2** | Daily dynamic state | `task_executions` + `feedbacks` + pre-task state history + read-only Level 1 profile | `fatigue` / `stress` / `self_efficacy` (value + uncertainty), behavioral indicators, next-day prior | `ddsr/config.json` + code; `model_version=ddsr_v1`, `artifact_version=ddsr_v1_config_1` | `UserModelService.refresh_dynamic_state` replays DDSR-V1 and persists the profile; `RepoContextBuilder` reads the snapshot |
| **Level 3** | Per-task outcome prediction | Level 1 trait + pre-task Level 2 state + task + context + real execution history | `completion_probability` (nullable), `predicted_duration_minutes`, uncertainty/interval, `prediction_mode`, `prediction_status`, support counts | `level3/*.py`; `model_version=level3_v1`, `feature_version=level3_features_v1` | **Shadow only**: `Level3ShadowRunner` after plan persistence; `mode=shadow` |

### 2.1 Typed contracts

All boundaries use `app/user_models/contracts.py`:

* `ModelMetadata` — level, model version, artifact version, artifact hash,
  feature version, mode, status, degraded reason.
* `TraitSnapshot` — Level 1 domains + metadata.
* `DynamicStateSnapshot` — Level 2 estimates + next-day prior + audit JSON.
* `HistoryBundle` — real execution counts / completion flags / duration ratios.
* `UserModelContext` — the only shape passed to the agent.
* `Level3Prediction` — nullable completion probability; cold start never invents
  one.

`PlanningContext.user_model` carries `UserModelContext` into the graph. No node
loads artifacts or reads a raw model dict.

### 2.2 Level 1 storage

`users.trait_profile` (JSON) + `trait_model_version`, `trait_artifact_hash`,
`trait_feature_version`. MBTI columns remain only as a soft self-report hint and
are never converted into a second trait estimate.

### 2.3 Level 2 storage and update

`user_states` keeps the audit JSON in `level2_profile` plus query-friendly
projections (`state_fatigue`, `state_stress`, `self_efficacy`,
`*_uncertainty`, `level2_profile_date`, `level2_model_version`,
`level2_config_version`, `level2_artifact_hash`, `level2_updated_at`).

`UserModelService.refresh_dynamic_state`:

1. Loads the validated Level 1 profile.
2. Builds `DayInput` records from real tasks / executions / feedbacks
   (only days up to today; future scheduled tasks are ignored).
3. Replays DDSR-V1 and persists the latest profile.
4. Is invoked after feedback and after task execution, best-effort.

The legacy `user_states` float fields are projections/display compatibility only;
there is no EWMA engine anymore (`app/domain/profile/engine.py` deleted).

---

## 3. Level 3 Shadow Mode

### 3.1 Data flow

```text
production path:
  UserModelContext + deterministic estimator
    -> plan drafts -> Scheduler -> RuleEngine -> persisted Plan/Task (commit)
                                                      │
                                                      ▼
shadow sidecar (after commit, same frozen inputs):
  Trait + pre-task State + Task + History
    -> Level3.predict -> validate -> shadow_predictions row
```

The shadow runner is called by `PlanService._run_level3_shadow` **after**
`_persist_final_plan` commits. It receives typed snapshots, not ORM objects, and
its return value is never used by the scheduler or rule engine.

### 3.2 Recorded fields (`shadow_predictions`)

`user_id`, `plan_id`, `task_id`, `inference_timestamp`, `model_level`,
`model_version`, `artifact_hash`, `artifact_version`, `feature_version`,
`input_hash`, `input_summary`, `production_decision`, `shadow_prediction`,
`confidence`, `uncertainty`, `disagreement`, `latency_ms`, `success`,
`failure_reason`, `degraded`, `mode`, `created_at`.

`input_summary` contains versions/support counts/state date — no raw prompts or
reflection text.

### 3.3 Failure policy

`Level3ShadowRunner.run` catches every exception, records `success=False` and a
structured `failure_reason`, and returns. `PlanService` wraps persistence in its
own try/except and commits shadow rows separately. A missing Level 1/2 snapshot
is recorded as a failed shadow attempt (`level1_unavailable` /
`level2_unavailable`), not as a production error.

### 3.4 Configuration

`LEVEL3_MODE=off|shadow|active`, default `shadow`.

* `off` — no Level 3 call.
* `shadow` — run + log; never control.
* `active` — parsed and **downgraded to shadow** with
  `mode_reason=active_not_open`. Production activation is explicitly not open in
  v1.

### 3.5 Why production is invariant

* The runner is invoked after the plan transaction commits.
* It can only append to `shadow_predictions`.
* No node reads `shadow_predictions` or `Level3Prediction`.
* `test_shadow_invariance.py` persists the same deterministic plan with Level 3
  `off` and `shadow` and asserts identical task fields, plus shadow rows present
  only in the shadow run.
* `test_user_models.py::test_shadow_runner_never_mutates_production_inputs`
  proves the production decision dict is unchanged.

---

## 4. LangGraph

### 4.1 Planner runtime + explicit workflows

`app/agent/graph.py` compiles **two** graphs and exposes four workflow entry
points through `PlannerRuntime`:

| Workflow | Entry | Graph |
| --- | --- | --- |
| `InitialPlanningWorkflow` | `start_initial` | `initial` |
| `PreviewAdjustmentWorkflow` | `resume_preview(action="adjust")` | `initial` (resume) |
| `PreviewConfirmWorkflow` | `resume_preview(action="confirm")` | `initial` (resume) |
| `FeedbackReplanWorkflow` | `run_feedback` | `replan` |
| `ManualReplanWorkflow` | `run_manual_replan` | `replan` |

The workflow is explicit in `PlannerState["workflow"]`; nodes never infer it from
free text. `PlannerGraph` remains as a deprecated alias for `PlannerRuntime`.

### 4.2 Initial graph

```text
START -> load_context -> goal_analysis -> theoretical_analysis
      -> user_situation_analysis -> plan_generation -> rule_validation
      -[should_repair]-> plan_repair -> rule_validation
      -> preview (interrupt)
         |- adjust  -> plan_generation
         |- confirm -> plan_finalization -> END
```

* The only interrupt is `preview` (`langgraph.types.interrupt`).
* `thread_id` == frontend `draft_id`; confirm/adjust resume the same thread.
* `preview` sets `workflow=preview_adjust` or `preview_confirm` on resume.

### 4.3 Replan graph

```text
START -> load_context -> process_feedback -> adjustment_decision
      -> adjustment_router
         |- NO_CHANGE    -> END
         |- MICRO_ADJUST -> micro_adjustment -> rule_validation
         |- FULL_REPLAN  -> goal_analysis -> theoretical_analysis
                         -> user_situation_analysis -> plan_generation
                         -> rule_validation
      -> [repair loop]
      -> plan_finalization -> END
```

`adjustment_decision` uses the deterministic domain policy. When the feedback
service has already decided the route, `PlannerRequest.feedback_route` is passed
through so the graph cannot re-derive a contradictory route.

### 4.4 Shared nodes / removed duplication

Shared by both graphs: `load_context`, `goal_analysis`, `theoretical_analysis`,
`user_situation_analysis`, `plan_generation`, `rule_validation`, `plan_repair`,
`plan_finalization`. The edge chain is built by one helper
(`_add_generation_chain`).

Removed:
* `classify_request` node (unused `classify` state).
* `ml_prediction` node (mock ML).
* `new_plan` wrapper (now the single `plan_finalization` node, with
  `workflow`-based `trigger_source`).
* Duplicate edge wiring between Graph A and Graph B.

### 4.5 Audit/SSE semantics

Every node publishes `node.started` / `node.completed`; `load_context` also
publishes `context_built`, `adjustment_decision` publishes `model_inference`, and
the runtime publishes `workflow_started`. SSE stage names still equal node names
(`GenerationService._frame`), so the frontend contract is unchanged.

`plan_finalization._trigger_source` now emits `manual_replan`,
`feedback_full_replan`, `micro_adjust`, `preview_adjusted` or `initial_plan`.
`PlanService._persist_final_plan` maps these to `ReplanTriggerType.MANUAL` vs
`FEEDBACK_TRIGGERED` and always writes a `ReplanEvent` for replan paths.

---

## 5. Database

New revision: **`ffc6c69463aa`** (`down_revision=533f463aff00`).

### 5.1 New table

`shadow_predictions` — append-only Level 3 audit (fields in §3.2) with indexes on
`user_id`, `plan_id`, `task_id`, `inference_timestamp`, `created_at`.

### 5.2 Changed tables

| Table | Change |
| --- | --- |
| `users` | `trait_profile` JSON, `trait_model_version`, `trait_artifact_hash`, `trait_feature_version` |
| `user_states` | `state_stress`, `state_fatigue_uncertainty`, `state_stress_uncertainty`, `self_efficacy_uncertainty`, `level2_profile` JSON, `level2_profile_date`, `level2_model_version`, `level2_config_version`, `level2_artifact_hash`, `level2_updated_at` |
| `tasks` | `prediction_source`, `prediction_mode` |

The migration adds server defaults for the new non-null `user_states` floats so
existing rows migrate. The autogenerated LangGraph checkpoint-table drops were
removed manually; those tables are owned by LangGraph.

Verified: `alembic upgrade head`, `alembic downgrade -1`,
`alembic upgrade head` all succeeded against the dev database. Test DBs are
created from `Base.metadata.create_all`.

---

## 6. Deleted / replaced content

### Deleted production mocks

* `app/ml/duration_predictor.py` — statistical duration mock.
* `app/ml/completion_predictor.py` — statistical completion mock.
* `app/ml/stress_predictor.py` — statistical stress mock.
* `app/ml/time_predictor.py` — statistical time-slot mock.
* `app/ml/adjustment.py` — rule-based + `MockAdjustmentPredictor`.
* `app/ml/predictors.py`, `app/ml/base.py`, `app/ml/__init__.py`.
* `app/infrastructure/ml/model_store.py` — unused placeholder store.

Production now uses `TaskEstimatorTool`:
* duration = the task's own theory-derived estimate;
* `completion_probability = None` (no trained production completion model);
* stress = Level 2 stress projection when available;
* time slot = the user's configured preference, otherwise none;
* source = `deterministic:workload_estimate`.

### Deleted old portrait logic

* `app/domain/profile/engine.py` — EWMA, MBTI templates, `replan_decision`,
  `predict_duration`, `predict_completion`.
* `app/domain/profile/mbti_templates.py`.
* `ProfileService.update_from_feedback`, `replan_decision_for`,
  `predict_*` runtime paths.
* `UserSituationResult` no longer receives fabricated completion probabilities.

MBTI remains a soft self-report field on `users`; it is not converted into model
state or a second trait estimate.

### Deleted dead nodes / code

* `app/agent/nodes/classify.py` (`classify_request`).
* `app/agent/nodes/prediction.py` (`ml_prediction`).
* `app/agent/nodes/replan.py` (`new_plan` wrapper).
* `ClassifyPolicy`, `ClassifyResult`, `low_completion_threshold`.
* `UserFeatureSet.duration_factor` (old predictor feature).

---

## 7. Compatibility

### Kept unchanged (wire-level)

* `POST /plans/generate`, `/preview`, `/preview/{thread_id}/confirm`,
  `/preview/{thread_id}/adjust`, `/decompose`, `/confirm`
* `GET /plans`, `/plans/{id}`, `/plans/{id}/changes`,
  `/plans/generation/{job_id}` (+ SSE)
* `POST /plans/{id}/replan`, `GET /plans/{id}/replan/eligibility`
* `POST /plans/{id}/feedback`, `GET /plans/{id}/feedback`
* `PATCH /plans/{plan_id}/tasks/{task_id}`, `DELETE ...`
* `/users/me`, `/users/me/profile`, `/users/me/preferences`,
  `/users/me/situation/trends`
* Preview interrupt/confirm/adjust and the 202 job + SSE flow.

### Additive fields

* `TaskRead.prediction_source`, `TaskRead.prediction_mode`
* `TaskUpdateRequest.completion_rate`
* `ProfileRead.trait`, `ProfileRead.state`, `ProfileRead.state_stress`,
  `ProfileRead.model_metadata`
* `UserRead.trait_profile`, `UserUpdate.trait_profile`
* `GET /users/me/model-runtime` (dev/debug: modes, artifact hashes, shadow summary)

### Behaviour changes (not schema breaks)

* Production `completion_probability` is now `null` (previously the mock value
  `0.65`). Frontend types already accept `number | null`.
* Production `predicted_duration` equals the task's own estimate; it is no longer
  multiplied by a mock statistical factor.
* `prediction_logs` now contains only truthful deterministic estimates
  (`duration`, and `stress` when Level 2 is available).
* Feedback replans record `ReplanTriggerType.FEEDBACK_TRIGGERED` for both
  `micro_adjust` and `feedback_full_replan`; manual replans record `MANUAL`.
* `changed_task_ids` is now a real diff against the previous version, not every
  task of the new version.

### Deprecated

* `PlannerGraph` — alias for `PlannerRuntime`; remove after one release.
* Legacy `user_states` float fields (`duration_factor`, `completion_prob`,
  `stress_baseline`, `energy_drain_rate`, `proactive_score`,
  `procrastination_tendency`, `stress_response`) — kept for wire compatibility;
  no runtime logic derives state from them.

---

## 8. Validation (actual results, 2026-10-24)

| Gate | Result |
| --- | --- |
| `uv sync --extra dev` | pass (numpy added) |
| `uv run alembic upgrade head` | pass |
| `uv run alembic downgrade -1` | pass |
| `uv run alembic upgrade head` (again) | pass |
| `uv run pytest` | **202 passed** in ~48 s |
| `uv run ruff check .` | **All checks passed** |
| `npm run typecheck` (new_frontend) | pass |
| `npm run lint` (new_frontend) | pass |

New tests cover:

* Level 1 artifact load / metadata / malformed profile / unavailable model.
* Level 2 replay + typed snapshot + invalid trait context.
* Level 3 cold start (no fabricated probability) + history baseline.
* `off` / `shadow` / `active`-downgraded modes.
* Shadow failure containment and input immutability.
* Production invariance with shadow off vs on (`test_shadow_invariance.py`).
* Architecture boundaries (`test_architecture.py`).

---

## 9. Shadow validation

**Runtime data: not enough runtime data.**

The code paths are implemented and tested, but the process has not accumulated
real production shadow rows across users/plans. Therefore no success rate,
failure count or disagreement distribution is reported here — inventing those
numbers would be dishonest.

What can be asserted from the automated tests:

* Shadow rows are written after the plan commit.
* Level 3 failure (including a raised exception) is recorded and does not fail
  the plan.
* Production task fields are identical with shadow `off` and `shadow`.
* A missing Level 1/2 snapshot is recorded as a failed shadow attempt, not as a
  production error.

The dev endpoint `GET /users/me/model-runtime` exposes
`shadow_summary` (`runs`, `success_rate`, `failures`, `mean_disagreement`,
`status`) so real data can be collected without a new migration.

---

## 10. Remaining risks / known limits

1. **Level 2 requires a Level 1 trait profile.** Without a valid
   `users.trait_profile`, dynamic state is not updated; the system degrades to
   observed aggregates and records `level1_unavailable` / `level2_unavailable`.
   There is no CAT questionnaire UI yet; profiles must be imported via
   `PATCH /users/me` (`trait_profile`) or a future assessment flow.
2. **Level 2 replays all history on each refresh.** Fine for the current data
   volume, but O(n) per feedback/execution. A persisted incremental cursor should
   replace it when history grows.
3. **Shadow is not shown in the user UI.** It is observable via the dev endpoint
   and `shadow_predictions`, not the product screens (intentional).
4. **`active` is not open.** It parses and downgrades to shadow. Enabling real
   Level 3 control requires an explicit calibration/eligibility decision and a
   new production policy.
5. **Scheduler / RuleEngine still duplicate some capacity checks.** They were not
   collapsed in this pass to avoid changing the hard-constraint authority or the
   scheduler's placement heuristics; the RuleEngine remains the final authority.
6. **Generation jobs and the SQLite checkpointer remain process-local.** Preview
   state does not survive a restart on SQLite; this was out of scope.
7. **`prediction_logs` now scores deterministic estimates**, not a trained model.
   The evaluation script remains valid for MAE/Brier plumbing but should not be
   read as model accuracy.
8. **Legacy `user_states` fields are stale by design.** They are projections /
   compatibility fields; do not use them as a second state source.