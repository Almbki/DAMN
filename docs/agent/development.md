# Developing the Agent

## 1. Setup

```bash
uv sync --extra dev
Copy-Item .env.example .env        # then edit
uv run pytest tests/agent -q
```

Relevant `.env` keys:

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./dev.db` | Postgres switches the checkpointer too |
| `AGENT_CHECKPOINTER` | `auto` | `auto` / `postgres` / `memory` |
| `AGENT_MAX_PREVIEW_ADJUSTMENTS` | `2` | preview adjustment budget |
| `AGENT_MAX_REPAIR_ATTEMPTS` | `2` | repair loop budget |
| `AGENT_LLM_MAX_RETRIES` | `2` | structured-output retries |
| `AGENT_GRAPH_VERSION` / `AGENT_PROMPT_VERSION` | `planner-v1` / `v1` | recorded in run metadata |
| `LLM_PROVIDER` | `mock` | `mock` needs no key; any other value uses `HttpLLMClient` |

## 2. Checkpointer

Preview/confirm/adjust **requires** a checkpointer (`interrupt()`).

| Mode | When | Trade-off |
| --- | --- | --- |
| `postgres` | `DATABASE_URL` is Postgres and reachable | paused previews survive restarts / multiple workers; needs `PostgresSaver.setup()` (automatic) |
| `memory` | anything else | zero setup; **paused previews are lost on restart** |

`app/agent/checkpointer.py` logs loudly when it degrades from Postgres to
memory. Verify what is actually in use:

```bash
uv run python -c "from app.agent.checkpointer import get_checkpointer_mode, get_checkpointer; get_checkpointer(); print(get_checkpointer_mode())"
```

Postgres evidence (verified locally, PostgreSQL 17.11, `planner@127.0.0.1:5432/planner`):

```
resolved checkpointer: postgres
after setup: [..., 'checkpoint_blobs', 'checkpoint_migrations', 'checkpoint_writes', 'checkpoints', ...]
```

## 3. Run

```bash
uv run uvicorn app.main:app --reload
# /docs for the OpenAPI surface
```

## 4. Driving the agent by hand

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","password":"password123"}' | jq -r .access_token)

# 1. preview (pauses the graph)
curl -s -X POST localhost:8000/api/v1/plans/preview \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"goals":[{"title":"复习高数极限","description":"看课\n做例题","subject":"math","estimated_minutes":120,"priority":3}]}' | jq

# 2. confirm (thread_id from the response)
curl -s -X POST localhost:8000/api/v1/plans/preview/$THREAD/confirm \
  -H "Authorization: Bearer $TOKEN" | jq '.plan | {version, tasks: (.tasks|length)}'
```

In Python (faster for iteration):

```python
from app.agent.checkpointer import get_checkpointer
from app.agent.state import PlannerRequest, GoalInput
from app.application.services.plan_service import PlanService
from datetime import date, timedelta

svc = PlanService(session, checkpointer=get_checkpointer())
preview = svc.generate_preview(user_id, PlannerRequest(
    user_id=user_id, start_date=date.today(), end_date=date.today()+timedelta(days=13),
    goals=[GoalInput(title="math", subject="math", estimated_minutes=120)],
))
print(len(preview.preview.tasks), preview.preview.can_adjust)
```

## 5. Inspecting a paused preview

```python
graph = svc._graph()                       # or PlannerGraph(ctx, checkpointer=...)
state = graph.pending_state(thread_id)     # None when the thread finished
print(state["adjustment_count"], state["notes"][-3:])
```

LangGraph also stores the thread in the `checkpoints` tables; a raw peek helps
when a resume misbehaves:

```sql
select thread_id, checkpoint_id, metadata->>'step' from checkpoints order by checkpoint_id desc limit 5;
```

## 6. Tracing a run

**Persisted trace (P1).** Every graph call opens and closes an `agent_runs` row
(`status`, `nodes_executed`, `tool_calls`, `llm_calls`, `plan_id`,
`result_summary`, `error`). Only counts and small summaries are stored — no
prompt bodies, no tool payloads, no free text.

```bash
uv run python -c "
import os
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import AgentRunRepository
s = SessionLocal()
for r in AgentRunRepository(s).list_by_user(1, limit=5):
    print(r.trigger_type, r.status, r.plan_id, r.nodes_executed)
    print('  tools:', [(c['tool'], c['ok']) for c in r.tool_calls])
    print('  summary:', r.result_summary)
"
```

**In-process events.** `RunEvents` collects everything emitted by the graph:

```python
from app.agent.graph import RunEvents
events = RunEvents()
detail, _events = svc.generate_plan_with_events(user_id, request)   # events reused
for e in events:
    print(e["event"], e.get("node") or "", e.get("summary") or "")
```

Event names: `agent.started`, `node.started`, `node.completed`,
`tool.completed`, `ml.started`, `ml.completed`, `waiting_user_confirmation`,
`preview.generated`, `plan.generated`, `replanning.started`,
`replanning.completed`, `agent.completed`. SSE re-emits node events under the
node name, so the documented stage contract still holds.

> `preview` publishes `node.started` but never `node.completed` on the first pass
> (the interrupt aborts the node). That is why `nodes_executed` is derived from
> both event kinds.

## 6b. Scoring the predictors (P1)

```bash
uv run python scripts/evaluate_predictors.py                     # all users
uv run python scripts/evaluate_predictors.py --user-id 3
uv run python scripts/evaluate_predictors.py --min-samples 5     # flag small samples
```

Joins `prediction_logs` with `task_executions` and prints:

| Metric | Meaning |
| --- | --- |
| `duration_mae_minutes` | MAE of predicted vs actual minutes |
| `completion_mae` / `completion_brier` | MAE and Brier of P(completion) vs observed completion rate |
| `stress_mae` | MAE of predicted vs reported stress-after |
| `time_slot_error_rate` | 0 = the recommended slot always matched the recorded time of day |

`n=0` means nothing could be scored yet (no reported executions) — it is never
faked. Lower is better; a trained model is only worth swapping in when it beats
the current `source` on the same rows.

```bash
# what produced the logged values (mock:statistical / fallback:rule / <model>)
uv run python -c "
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import PredictionLogRepository
s = SessionLocal()
for p in PredictionLogRepository(s).list_by_user(1, limit=10):
    print(p.prediction_type, p.source, p.predicted, p.feature_hash)
"
```

## 7. Forcing routes while developing

```python
from app.ml.adjustment import MockAdjustmentPredictor
from app.ml.base import AdjustmentRoute
ps = PredictorSet.default()
ps.adjustment = MockAdjustmentPredictor(AdjustmentRoute.FULL_REPLAN)
svc = PlanService(session, predictors=ps, checkpointer=get_checkpointer())
```

## 8. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `RuntimeError: PlannerContext missing` | the graph was invoked without `context=`; use `PlannerGraph`, which injects it |
| preview lost after restart | `checkpointer_mode == "memory"`; use Postgres (see §2) |
| `Deserializing unregistered type … from checkpoint` | benign with the current serde; tightening the allowlist is a HARDENING TODO in `checkpointer.py` |
| plan saved with 0 tasks | the goals were not committed before the graph ran, or the goal chain is broken — see `docs/agent/data-flow.md` |
| `completion_probability` is always `1.0` | predictions are not being written onto the drafts (`GeneratedTaskDraft.completion_probability`); the scheduler's `or 1.0` fallback masks it |
| LLM results look like the deterministic ones | `LLM_PROVIDER=mock` or the schema validation failed and fell back — check `StructuredResult.used_llm` |
| replan returns 409 | per-user cooldown (`SCHEDULER_MIN_REPLAN_INTERVAL_HOURS`); this is expected |
| prompt edit has no effect in a test | `app.agent.prompts.clear_prompt_cache()` |

## 9. Conventions

- A node orchestrates; a tool does the work; a prompt defines behaviour.
- Validate before writing state; never let a model decide a hard constraint.
- Always provide a deterministic fallback so `uv run pytest` never depends on a
  network or a key.
- Keep `source` truthful on every prediction.
