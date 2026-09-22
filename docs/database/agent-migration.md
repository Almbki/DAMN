# Database Impact — Agent Layer

Two phases are recorded here:

| Phase | Schema impact | Migration |
| --- | --- | --- |
| **P0** (agent skeleton) | none | — |
| **P1** (memory + observability) | 3 new tables | `7f9ae3f96ba3` |

Current head:

```
$ uv run alembic current
7f9ae3f96ba3 (head)
```

---

## P0 — no migration was required

1. **The preview is not persisted.** `POST /plans/preview` writes only the
   `goals` rows; the candidate plan, tasks and the paused state live in the
   LangGraph checkpoint. Plan/task rows are created only on confirm or on a
   feedback-driven adjust/replan.
2. **Plan status reuses the existing enum.** `PlanStatus` already had
   `draft / active / superseded / completed / archived`; a preview never reaches
   the `plans` table.
3. **The ML plumbing fix needed no DDL.** `tasks.predicted_duration` and
   `tasks.completion_probability` already existed — the bug was that
   `completion_probability` was written as the scheduler default `1.0` because the
   predicted value never reached the draft (a code fix).
4. **Cooldown reuses `replan_events`** via
   `ReplanEventRepository.get_latest_for_user()` (a JOIN over the existing
   `replan_events` → `plans`).

LangGraph's own checkpoint tables (`checkpoints`, `checkpoint_blobs`,
`checkpoint_writes`, `checkpoint_migrations`) are created by
`PostgresSaver.setup()` in `build_checkpointer()` — **not** by Alembic.

---

## P1 — migration `7f9ae3f96ba3`

Three new tables. **No existing table or column was altered, renamed or
dropped**, so existing rows are unaffected.

### `agent_runs` — audit trail for agent executions

| Column | Type | Notes |
| --- | --- | --- |
| `id` | int PK | |
| `run_id` | str(64) | unique, indexed — correlates with the LangGraph `thread_id` |
| `user_id` | FK `users.id` | indexed |
| `plan_id` | FK `plans.id` nullable | indexed; filled after persistence |
| `trigger_type` | str(32) | `initial_plan`, `confirm_preview`, `preview_adjusted`, `feedback_cycle`, `replan` |
| `graph_version` / `prompt_version` | str(32) | which code/prompt produced the run |
| `status` | str(16) | `running` / `completed` / `failed`, indexed |
| `started_at` / `finished_at` | timestamptz | |
| `nodes_executed` | JSON | node names in order — **names only** |
| `tool_calls` | JSON | `{tool, ok, duration_ms, summary}` — **no payloads** |
| `llm_calls` | int | derived from the `StructuredLLM` call counter |
| `ml_prediction_id` | int nullable | reserved link to the adjustment prediction |
| `result_summary` | JSON | small: stage, route, version, task count, confidence, degraded |
| `error` | str(2000) nullable | |

Privacy: **no prompt bodies, no free-text user input, no tool payloads.**

### `prediction_logs` — so predictions can be scored

| Column | Type | Notes |
| --- | --- | --- |
| `id` | int PK | |
| `user_id` | FK `users.id` | indexed |
| `plan_id` | FK `plans.id` nullable | indexed |
| `task_id` | FK `tasks.id` nullable | indexed; null for plan-level predictions |
| `model_name` | str(64) | the predictor that produced the value |
| `model_version` | str(32) | |
| `prediction_type` | str(32) | `duration` / `completion` / `stress` / `time_slot` / `adjustment`, indexed |
| `feature_hash` | str(64) | sha256[:16] fingerprint of the feature vector |
| `predicted` | JSON | e.g. `{"predicted_minutes": 138}` |
| `source` | str(64) | truthful origin: `mock:statistical`, `fallback:rule`, `llm`, `<trained model>` |
| `created_at` | timestamptz | indexed |

Written by `PlanService._log_predictions()` whenever a plan version is persisted.
Read by `scripts/evaluate_predictors.py`.

### `agent_memories` — persisted semantic / episodic / procedural memory

| Column | Type | Notes |
| --- | --- | --- |
| `id` | int PK | |
| `user_id` | FK `users.id` | indexed |
| `kind` | str(16) | `semantic` / `episodic` / `procedural`, indexed |
| `key` | str(128) | stable slug |
| `value` | JSON | |
| `summary` | str(500) | prompt-friendly line |
| `confidence` | float | |
| `source` | str(64) | provenance (`users.profile`, `task_executions`, `feedbacks`, ...) |
| `updated_at` | timestamptz | |

Unique constraint `uq_agent_memories_user_kind_key` on `(user_id, kind, key)` so
memory stays consolidated (upsert, not append). Episodic rows accumulate and are
pruned to the most recent `EPISODIC_KEEP = 50` per user.

Written by `MemoryService.refresh()` (called after each feedback submission).
Read by `RepoContextBuilder` and merged over freshly derived memory
(`merge_memory()` — persisted rows win per key).

### Why these three

| Table | Question it answers |
| --- | --- |
| `agent_runs` | "what actually ran, and why did it fail?" |
| `prediction_logs` | "is the model any good?" (MAE / Brier / calibration) |
| `agent_memories` | "what have we learned about this user that we cannot re-derive?" |

### Upgrade

```bash
uv run alembic upgrade head      # 4e95b02e3696 -> 7f9ae3f96ba3
uv run alembic current           # 7f9ae3f96ba3 (head)
uv run pytest                    # 94 passed
```

Verified locally against PostgreSQL 17.11 (`planner@127.0.0.1:5432/planner`):
the three tables and their columns are present after the upgrade.

### Rollback

```bash
uv run alembic downgrade -1      # 7f9ae3f96ba3 -> 4e95b02e3696, drops the 3 tables
uv run alembic upgrade head      # re-apply
```

Round-trip verified. The downgrade drops only `agent_runs`, `prediction_logs`
and `agent_memories`; no business data (`plans`, `tasks`, `goals`, `feedbacks`,
`task_executions`) is touched.

### Operational notes

- `agent_runs` and `prediction_logs` grow with usage. Suggested retention:
  prune `agent_runs` older than 90 days and `prediction_logs` older than 365
  days (they are the training/evaluation audit trail, so keep them longer).
- `prediction_logs` intentionally duplicates a little of `tasks`
  (`predicted_duration`), because the task row is mutable while the prediction
  at plan time must be immutable for honest scoring.

---

## Hardening TODO (recorded, not done)

`app/agent/checkpointer.py::_build_serde()` currently allows all JSON/msgpack
modules (`allowed_json_modules=True`, `allowed_msgpack_modules=True`) because the
checkpoint database is our own. Before multi-tenant deployment this must become
an explicit `(module, attribute)` allowlist.

## Rules for future schema changes

1. add the SQLAlchemy model in `app/infrastructure/database/models/`
2. `uv run alembic revision --autogenerate -m "..."` (never hand-write)
3. review the generated migration (SQLite batch mode rewrites tables)
4. `uv run alembic upgrade head` and re-run `uv run pytest`
5. verify rollback: `uv run alembic downgrade -1`
6. record the reason, the DDL and the rollback command in this file
