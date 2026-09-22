# LangGraph Planning State Machine

> **SUPERSEDED (agent P0).** This document describes the first 6-node prototype.
> The agent layer now runs **two graphs** with preview/confirm/adjust, a feedback
> router and a run-scoped context. See:
> [`docs/agent/state-machine.md`](agent/state-machine.md) (graphs, nodes, edges)
> and [`docs/agent/README.md`](agent/README.md) (module map).
>
> What changed at a glance: nodes are now `load_context`, `classify_request`,
> `goal_analysis`, `theoretical_analysis`, `user_situation_analysis`,
> `plan_generation`, `rule_validation` (`nodes/validation.py`), `plan_repair`
> (`nodes/repair.py`), `preview`, `plan_finalization`, plus the feedback-graph
> nodes `process_feedback`, `ml_prediction`, `adjustment_router`,
> `micro_adjustment`, `new_plan`. Dependencies moved out of `PlannerState` into
> `PlannerContext` (LangGraph `context_schema`), so state is now checkpointable.

Code: `app/agent/graph.py`, `app/agent/state.py`, `app/agent/schemas.py`,
`app/agent/nodes/*`, orchestrated by `PlanService.generate_plan_with_events`.

> **LangGraph orchestrates only.** It never opens a database session and never
> decides whether a hard constraint holds — the Rule Engine
> (`app/domain/rules/`) does that. All agent output is structured Pydantic
> (`app/agent/schemas.py`); free-form LLM text never flows into the plan.

---

## 1. Flow

```
              START
                │
                ▼
        ┌───────────────┐
        │ goal_analysis │
        └───────┬───────┘
                ▼
      ┌──────────────────────┐
      │ theoretical_analysis │
      └──────────┬───────────┘
                 ▼
    ┌───────────────────────────┐
    │ user_situation_analysis   │   ← injects UserFeatureSet + predictors
    └────────────┬──────────────┘
                 ▼
       ┌──────────────────┐
       │ plan_generation  │
       └────────┬─────────┘
                ▼
      ┌──────────────────┐        hard violations
      │  rule_validation │──────────────┐  and attempts < max
      └────────┬─────────┘              ▼
               │ no violations   ┌──────────────┐
               │                 │ plan_repair  │
               │                 └──────┬───────┘
               │                        │
               │                        ▼
               │                 ┌──────────────────┐
               │                 │  rule_validation │ (loop)
               │                 └──────┬───────────┘
               ▼                        ▼
              END ◄─────────────────────┘
```

The conditional edge is `should_repair(state)` in `app/agent/graph.py`:

```python
hard = [v for v in state.rule_violations if v.is_hard]
attempts = state.repair_attempts
max_attempts = state.max_repair_attempts   # default 2
return "repair" if (hard and attempts < max_attempts) else "end"
```

Node names (`app/agent/graph.py::NODE_ORDER`): `goal_analysis`,
`theoretical_analysis`, `user_situation_analysis`, `plan_generation`,
`rule_validation`, `plan_repair`. These are exactly the SSE stage names
(`completed` is appended by `GenerationService`).

**Fallback:** if `langgraph` cannot be imported (or graph construction raises),
`PlannerGraph` falls back to a deterministic sequential executor implementing
the same node order and repair loop (`_execute_sequential`), so the service and
the project always start.

---

## 2. Nodes

| Node | Input (from state) | Output (state keys) | Responsibility | Status |
| --- | --- | --- | --- | --- |
| `goal_analysis` | `goals`, `user_profile` | `goal_analysis: GoalAnalysisResult` | Turn raw goals into objective + subtasks + constraints | **MOCK** heuristic (`GoalAnalysisAgent`) |
| `theoretical_analysis` | `goals`, `goal_analysis` | `theoretical_workload: TheoreticalAnalysisResult` | Estimate video/reading/practice minutes, difficulty, cognitive load | **MOCK** heuristic (`TheoreticalAnalysisAgent`) |
| `user_situation_analysis` | `theoretical_workload`, `user_features`, `predictors` | `user_situation`, `predicted_duration`, `predicted_completion_probability`, `stress_estimation` | Apply the four ML predictors to the provisional tasks | **MOCK** statistical predictors via `PredictorSet` |
| `plan_generation` | `theoretical_workload`, `user_situation`, `goals`, `goal_id_map`, `request` | `plan_draft: PlanGenerationResult` | Produce structured `GeneratedTaskDraft`s | **MOCK** heuristic (`PlanGenerationAgent`) |
| `rule_validation` | `plan_draft`, `request`, `scheduler`, `rule_engine` | `candidate_plan`, `rule_violations`, `rule_validation` | Schedule (heuristic) then validate with `RuleEngine.hard_violations` | Real Domain logic |
| `plan_repair` | `plan_draft`, `rule_violations`, `candidate_plan`, `scheduler`, `rule_engine` | `repaired_plan`, `final_tasks`, `final_plan`, `rule_violations`, `rule_validation`, `repair_attempts` | Bounded deterministic repair, then re-schedule + re-validate | **MOCK** strategy (`PlanRepairAgent`, max 5 drops) |

### Node details

**`goal_analysis`** — objective = `description or title`; subtasks parsed by
splitting the description on newlines / `;` / `；` / `|` (fallback: 2–4 generic
stages inferred from subject/task type). Confidence `0.6` if any goal carries
`estimated_minutes`, else `0.45`. `AnalyzedGoal.goal_id` is the 1-based goal
index ("goal_key").

**`theoretical_analysis`** — with `estimated_minutes` present: 30 % video /
30 % reading / 40 % practice; otherwise subject/task-type defaults
(math/algorithm/408 → 120, language → 60, reading/writing → 90, fallback 90).
`cognitive_load` from keyword mapping (math/algorithm/408/physics → HIGH,
english/线代/code → MEDIUM, exercise/music/rest → RESTORATIVE, else LOW).
`difficulty` 4.0/3.0/2.0/1.5 by load.

**`user_situation_analysis`** — builds `TaskFeatureSet` per task and calls
`predictors.duration/completion/stress/time_slot.predict(PredictionRequest)`.
Aggregates mean duration factor, mean completion probability, mean stress, worst
`LoadLevel`, modal time slot, and `should_reduce_load` (OR of stress flags).

**`plan_generation`** — one `GeneratedTaskDraft` per `TheoreticalItem`; duration
= item total, predicted duration from `user_situation.predicted_duration`,
subject/priority/deadline from the matching `GoalInput`, standards = subtasks.

**`rule_validation`** — `build_rule_context(state)` then
`scheduler.schedule(tasks, context)` then
`rule_engine.hard_violations(schedule, context)`.

**`plan_repair`** — collects offending task ids from violations plus
`candidate_plan.unscheduled_task_ids`, drops the lowest-priority draftee
(bounded to `MAX_DROPS_PER_REPAIR = 5`), re-indexes `order_index`, re-schedules
and re-validates.

---

## 3. State — `PlannerState` (`app/agent/state.py`)

`TypedDict(total=False)`; LangGraph merges node updates.

| Key | Type | Set by | Meaning |
| --- | --- | --- | --- |
| `user_id` | `int` | Service | owner (never used for DB access inside the graph) |
| `goals` | `list[GoalInput]` | Service | input goals |
| `user_profile` | `dict` | Service | free-form profile |
| `request` | `GenerationRequest` | Service | limits/horizon/title |
| `goal_analysis` | `GoalAnalysisResult` | node 1 | |
| `theoretical_workload` | `TheoreticalAnalysisResult` | node 2 | |
| `user_situation` | `UserSituationResult` | node 3 | |
| `plan_draft` | `PlanGenerationResult` | node 4 | |
| `candidate_plan` | `CandidateSchedule` | node 5 | scheduler output |
| `rule_validation` | `RuleValidationResult` | nodes 5/6 | |
| `rule_violations` | `list[RuleViolation]` | nodes 5/6 | |
| `repaired_plan` | `PlanRepairResult` | node 6 | |
| `predicted_duration` | `dict[int, int]` | node 3 | provisional id → minutes |
| `predicted_completion_probability` | `dict[int, float]` | node 3 | provisional id → 0..1 |
| `stress_estimation` | `float` | node 3 | mean predicted stress |
| `repair_attempts` | `int` | node 6 | loop guard |
| `max_repair_attempts` | `int` | Service | default 2 |
| `final_tasks` | `list[GeneratedTaskDraft]` | node 6 | post-repair drafts |
| `final_plan` | `CandidateSchedule \| None` | node 6 | post-repair schedule |
| `confidence` | `float` | *(computed by PlanService)* | mean of node confidences |
| `notes` | `list[str]` | all nodes | human-readable trace |
| `events` | `list[dict]` | reserved | |
| `user_features` | `UserFeatureSet` | Service | injected history features |
| `goal_id_map` | `dict[int, int]` | Service | goal_key → persisted goal id |
| `llm` | `object` | Service | optional `LLMClient` |
| `predictors` | `PredictorSet` | Service | |
| `scheduler` | `Scheduler` | Service | |
| `rule_engine` | `RuleEngine` | Service | |
| `theoretical_agent`, `situation_agent` | `object` | Service | optional overrides |

---

## 4. Provisional id contract

Tasks do not exist in the database while the graph runs. Every draft therefore
carries a **provisional id equal to `order_index + 1` (1-based)**, used
consistently by:

- `plan_generation.drafts_to_tasks`
- `rule_validation.build_rule_context` (`task_subjects`, `task_deadlines`)
- the `CandidateSchedule` produced by the Scheduler
- `plan_repair` (re-indexes `order_index`, so provisional ids stay dense)

`PlanService._persist_plan` maps the schedule by provisional id, persists real
`Task` rows, and drops the provisional ids.

---

## 5. Events for SSE

`PlannerGraph.run_with_events(...)` returns `(final_state, events)` where each
event is a `GenerationEvent`:

```json
{
  "node": "rule_validation",
  "stage": "rule_validation",
  "status": "completed",
  "summary": "rule_validation: 0 hard violation(s), 0 unscheduled",
  "payload": {},
  "progress": 0.83,
  "timestamp": "2026-09-19T11:38:56.737Z"
}
```

`GenerationService.stream_sse` formats each as `event: <stage>\ndata: <json>\n\n`
and appends `event: completed` with `{plan_id, status, job_id}` (or
`event: failed` with the error).

---

## 6. What LangGraph is **not** responsible for

| Not its job | Owner |
| --- | --- |
| DB sessions / commits | `PlanService` |
| Hard-constraint decisions | `RuleEngine` |
| Duration/completion/stress predictions | `app/ml` predictors |
| Calendar placement | `Scheduler` |
| Permission checks | Service + `deps.get_current_user` |
