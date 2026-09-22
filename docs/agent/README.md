# Agent Layer

The agent layer turns goals + history into a plan, and turns feedback into a
routing decision (`NO_CHANGE` / `MICRO_ADJUST` / `FULL_REPLAN`).

It is **not** a super-agent. It is a deterministic workflow that *uses* an LLM:

```
Deterministic workflow (LangGraph)
  + ML prediction      (app/ml)
  + LLM reasoning      (prompts + tools)
  + Rule Engine        (hard constraints)
  + Scheduler          (calendar placement)
  + User memory        (structured, no vector DB)
  + Feedback loop
```

## Documents

| Doc | Contents |
| --- | --- |
| [`state-machine.md`](state-machine.md) | Both graphs, every node, every edge |
| [`data-flow.md`](data-flow.md) | Request lifecycle + which layer touches the DB |
| [`dependencies.md`](dependencies.md) | Layer boundaries and dependency injection |
| [`prompts.md`](prompts.md) | The 7 prompts, format, how to change them |
| [`tools.md`](tools.md) | The 8 tools, LLM exposure, how to add one |
| [`ml-interface.md`](ml-interface.md) | Predictor interfaces + fallbacks |
| [`memory.md`](memory.md) | Semantic / episodic / procedural memory |
| [`testing.md`](testing.md) | Test layout + TEST 1..9 acceptance map |
| [`development.md`](development.md) | Run, inspect, resume, troubleshoot |
| [`../database/agent-migration.md`](../database/agent-migration.md) | Schema impact + rollback |

## "Where do I change what?"

| I want to… | Edit | Do NOT touch |
| --- | --- | --- |
| change LLM behaviour wording | `app/agent/prompts/*.md` | graph, nodes |
| add a capability (search, statistics, …) | `app/agent/tools/<new>.py` + register in `app/agent/tools/__init__.py` | graph |
| swap the ML model | implement the Protocol in `app/ml/`, inject via `PredictorSet` | graph, nodes, prompts |
| add/alter a hard constraint | `app/domain/rules/` + `default_rules()` | agent |
| change scheduling | `app/domain/scheduling/scheduler.py` | agent |
| change when we escalate to a full replan | `app/agent/router.py` (`AdjustmentRouter`) | nodes |
| change the workflow itself (rare) | `app/agent/graph.py` + a node module | prompts, tools |
| change what memory is recorded | `app/agent/memory/*.py` (derive) + `MemoryService` (persist) | graph |
| change what is audited | `PlanService._finish_run` / `_log_predictions` | graph |

## P1 additions (memory + observability)

| Piece | Where | Table |
| --- | --- | --- |
| Run audit trail | `PlanService._start_run/_finish_run/_link_run` | `agent_runs` |
| Prediction scoring input | `PlanService._log_predictions` | `prediction_logs` |
| Persisted memory | `MemoryService.refresh` / `RepoContextBuilder.merge_memory` | `agent_memories` |
| Offline evaluation | `scripts/evaluate_predictors.py` | reads `prediction_logs` + `task_executions` |
| Migration | `alembic/versions/7f9ae3f96ba3_*.py` | see [`../database/agent-migration.md`](../database/agent-migration.md) |

`agent_runs` stores **counts and summaries only** — no prompt bodies, no tool
payloads, no free-text input.

## Node → file index

| Node | File |
| --- | --- |
| `load_context` | `app/agent/nodes/context.py` |
| `classify_request` | `app/agent/nodes/classify.py` |
| `goal_analysis` | `app/agent/nodes/goal_analysis.py` |
| `theoretical_analysis` | `app/agent/nodes/theoretical_analysis.py` |
| `user_situation_analysis` | `app/agent/nodes/user_situation.py` |
| `plan_generation` | `app/agent/nodes/plan_generation.py` |
| `rule_validation` | `app/agent/nodes/validation.py` |
| `plan_repair` | `app/agent/nodes/repair.py` |
| `preview` | `app/agent/nodes/preview.py` |
| `plan_finalization` | `app/agent/nodes/finalization.py` |
| `process_feedback` | `app/agent/nodes/feedback.py` |
| `ml_prediction` | `app/agent/nodes/prediction.py` |
| `adjustment_router` | `app/agent/nodes/adjustment_router.py` |
| `micro_adjustment` | `app/agent/nodes/micro_adjustment.py` |
| `new_plan` | `app/agent/nodes/replan.py` |
