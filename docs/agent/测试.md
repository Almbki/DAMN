# Testing the Agent

## Run

```bash
uv run pytest                          # everything (94 tests)
uv run pytest tests/agent -q           # agent layer
uv run pytest tests/agent/test_preview_flow.py -v
uv run pytest tests/api/test_replan_cooldown.py -v
uv run pytest -k preview -v
```

Layout:

```
tests/
├── conftest.py                    # client / auth_headers / registered_user, test DB
├── unit/                          # security, rules, scheduler, ml
├── api/                           # auth, plans, replan cooldown (TEST 8/9)
├── integration/test_plan_flow.py  # closed loop through the legacy generate path
└── agent/
    ├── conftest.py                # route override + predictor fakes
    ├── test_preview_flow.py       # TEST 1, 2, 7
    ├── test_feedback_routes.py    # TEST 3, 4, 5
    ├── test_repair.py             # TEST 6
    ├── test_router.py             # policy unit tests
    ├── test_tools.py              # tool contracts
    ├── test_regressions.py        # A-class regression guards (config, confidence, degradation, predictor gating)
    └── test_p1_observability.py   # P1: agent_runs, prediction_logs, agent_memories, eval script
```

## Fixtures (`tests/agent/conftest.py`)

| Fixture / helper | Purpose |
| --- | --- |
| `client`, `auth_headers` | from `tests/conftest.py`; real FastAPI app + JWT |
| `goals`, `preview_payload` | a math + algorithm goal set (exercises the same-day conflict rule) |
| `override_plan_service(client, route=…, severity=…, max_preview_adjustments=…, max_repair_attempts=…)` | monkeypatches `get_plan_service` via `app.dependency_overrides` so a test can **force** the ML route and the budgets |
| `CHECKPOINTER` | one `InMemorySaver` shared across the agent tests (preview state must survive between two HTTP requests) |
| `RouteOverride().install(predictors)` | deterministic duration factor `1.5` and completion `0.65`, so ML plumbing is observable |

The override reuses the request-scoped session from `get_db`; creating a second
session would leak a connection and lock the SQLite test database.

`tests/conftest.py` sets `DATABASE_URL` / `JWT_SECRET_KEY` **before** importing
`app` and then clears the settings cache — keep that order in new tests.

## Acceptance map

| Spec | What it proves | Test |
| --- | --- | --- |
| TEST 1 | preview pauses → confirm persists v1, ML values survive | `tests/agent/test_preview_flow.py::test_preview_then_confirm_creates_plan_v1` |
| TEST 2 | adjust updates the preview (scaled durations) → confirm yields v1 | `…::test_preview_adjust_then_confirm` |
| TEST 3 | `NO_CHANGE` → no LLM, nothing persisted | `tests/agent/test_feedback_routes.py::test_feedback_no_change_keeps_plan` |
| TEST 4 | `MICRO_ADJUST` → scheduler + rules, new version v2 | `…::test_feedback_micro_adjust_creates_light_version` |
| TEST 5 | `FULL_REPLAN` → context + rebuild → v2 with goals preserved | `…::test_feedback_full_replan_creates_v2` |
| TEST 6 | violation → repair → revalidation → valid plan | `tests/agent/test_repair.py::test_deadline_violation_is_repaired_and_revalidated` |
| TEST 7 | budget exhausted → refuse further adjustments, finalise | `tests/agent/test_preview_flow.py::test_adjustment_budget_forces_execution` |
| TEST 8 | manual replan when eligible → new version | `tests/api/test_replan_cooldown.py::test_manual_replan_succeeds_when_eligible` |
| TEST 9 | cooldown blocks the next replan with a reason + next time | `…::test_manual_replan_blocked_by_cooldown` |

Additional guards worth knowing:

- `test_router.py` — the policy layer in isolation (fresh plan is **not**
  escalated, failing plan is, explicit requirement wins, ML pass-through).
- `test_tools.py::test_deterministic_tools_are_not_llm_exposed` — hard
  constraints, scheduling, statistics and memory lookup must never be given to a model.
- `test_repair.py` — the heuristic Scheduler is itself rule-aware, so repair is
  exercised with a violation it cannot avoid (a deadline already in the past).
- `test_regressions.py` — one test per A-class defect fixed after the P0 review:
  repair budget read from config, derived confidence (not hardcoded 0.5),
  degradation surfaced, `task_features` fallback, first-bad-day does **not**
  trigger a full rebuild.
- `test_p1_observability.py` — `agent_runs` rows (nodes/tools/summary, plan
  linkage, no payloads recorded), `prediction_logs` (every type, truthful
  `source`, feature fingerprint), `agent_memories` (persisted after feedback),
  `merge_memory` precedence, and that the evaluation script reports `n=0` rather
  than a fabricated number when nothing can be scored.

### P1 tests need the new tables

`tests/conftest.py` creates the schema with `Base.metadata.create_all`, so the P1
tables come for free. If you add a model, import it in
`app/infrastructure/database/models/__init__.py` or it will be missing from both
`init_db()` and Alembic autogenerate.

## Forcing each route in a test

```python
from app.ml.base import AdjustmentRoute, AdjustmentSeverity
from tests.agent.conftest import override_plan_service

override_plan_service(client, route=AdjustmentRoute.MICRO_ADJUST,
                      severity=AdjustmentSeverity.MEDIUM)
```

## Testing without an LLM

Pass `StructuredLLM(None)` (or leave `LLM_PROVIDER=mock`) — every tool falls back
deterministically, so assertions are stable. To test the *LLM path*, build a fake
client with a `complete(prompt, *, system, json_schema) -> LLMResponse` method
and assert that the returned schema validates (and that invalid JSON triggers the
fallback).

## Testing without Postgres

`tests/conftest.py` points `DATABASE_URL` at a file SQLite. The checkpointer then
resolves to `memory` (`Settings.checkpointer_mode` is `auto`), so the whole
preview flow is testable with zero services.
