> **状态提示（2026-10-25）**：本文件部分内容基于旧代码或旧节点，可能和当前 `V1.1-test` 不一致。当前实现以 [当前实现.md](../当前实现.md)、[模型与Agent集成-v1.md](../模型与Agent集成-v1.md) 和代码为准；目标设计见 [架构.md](../架构.md)。读实现前先看这一行。

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
| [`状态机.md`](状态机.md) | Both graphs, every node, every edge |
| [`数据流.md`](数据流.md) | Request lifecycle + which layer touches the DB |
| [`依赖.md`](依赖.md) | Layer boundaries and dependency injection |
| [`提示词.md`](提示词.md) | The 7 prompts, format, how to change them |
| [`工具.md`](工具.md) | The 8 tools, LLM exposure, how to add one |
| [`模型接口.md`](模型接口.md) | Predictor interfaces + fallbacks |
| [`记忆.md`](记忆.md) | Semantic / episodic / procedural memory |
| [`测试.md`](测试.md) | Test layout + TEST 1..9 acceptance map |
| [`开发.md`](开发.md) | Run, inspect, resume, troubleshoot |
| [`../database/数据库迁移.md`](../database/数据库迁移.md) | Schema impact + rollback |

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
| Migration | `alembic/versions/7f9ae3f96ba3_*.py` | see [`../database/数据库迁移.md`](../database/数据库迁移.md) |

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
