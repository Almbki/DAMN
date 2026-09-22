# State Machines

Two compiled LangGraph graphs, built in `app/agent/graph.py` with
`StateGraph(PlannerState, context_schema=PlannerContext)`. Dependencies reach
nodes through `runtime.context` (`PlannerContext`), **never** through the state.

- `GRAPH_A_VERSION = "initial-plan-v1"` — `build_initial_plan_graph()`
- `GRAPH_B_VERSION = "feedback-loop-v1"` — `build_feedback_loop_graph()`

---

## Graph A — initial plan (preview → confirm / adjust)

```
START
  │
  ▼
load_context ──► classify_request ──► goal_analysis ──► theoretical_analysis
                                                            │
                                                            ▼
                                                 user_situation_analysis
                                                            │
                                                            ▼
                                                     plan_generation
                                                            │
                                                            ▼
  ┌──────────────────────► rule_validation ◄─────────── plan_repair
  │                             │  ▲                        ▲
  │             should_repair() │  └────────────────────────┘
  │                             │  "repair"
  │                             ▼  "continue"
  │                          preview  ◄── interrupt() : WAITS FOR THE USER
  │                             │
  │        route_after_preview()│
  │            "revise" ┌───────┴────────┐ "finalize"
  │                     ▼                ▼
  └────────────► plan_generation   plan_finalization ──► END
```

`preview` calls LangGraph's `interrupt()`, so the run is checkpointed and the
HTTP request returns. The user resumes it with
`Command(resume={"action": "confirm" | "adjust", "feedback": ...})`.

**Adjustment budget.** `preview` reads `AgentConfig.max_preview_adjustments`
(`AGENT_MAX_PREVIEW_ADJUSTMENTS`, default 2). Once
`adjustment_count >= max_adjustments` the node refuses the adjustment, clears
`user_adjustment`, and `route_after_preview` sends the run to
`plan_finalization` — the user is pushed into execution instead of regenerating
forever.

---

## Graph B — feedback loop

```
START
  │
  ▼
load_context ──► process_feedback ──► ml_prediction ──► adjustment_router
                                                              │
                                    route_after_adjustment()  │
        ┌─────────────────────────────┬───────────────────────┴────────────┐
        │ "no_change"                 │ "micro_adjust"                     │ "full_replan"
        ▼                             ▼                                    ▼
       END                    micro_adjustment                     goal_analysis
                                      │                                    │
                                      ▼                                    ▼
                              rule_validation                     theoretical_analysis
                                 │    ▲                                    │
                    should_repair│    │"repair"                            ▼
                                 │    └── plan_repair              user_situation_analysis
                                 │                                          │
                                 ▼ "continue"                               ▼
                              new_plan ◄──────────────────────────── plan_generation
                                 │                                          │
                                 ▼                                          ▼
                                END                                  rule_validation
                                                                            │  ▲
                                                              should_repair │  └── plan_repair
                                                                            ▼ "continue"
                                                                         new_plan ──► END
```

- `NO_CHANGE` — **nothing is persisted**; the plan is untouched.
- `MICRO_ADJUST` — deterministic: `micro_adjustment` reuses the unfinished tasks
  and scales the daily limits by the predictor's
  `suggested_daily_limit_factor` (clamped to `[0.5, 1.0]`, stored as
  `state["limit_factor"]`). **No LLM call.** It still produces a new plan
  version, because §18 forbids overwriting a plan.
- `FULL_REPLAN` — the full analysis chain runs again through
  `plan_drafter` in `REPLAN` mode.

> Note: `load_context` is also CONTEXT_BUILD for the replan branch. The graph
> deliberately does **not** re-read the database after the router: the feedback
> was already persisted before the run started, so `load_context` already
> includes it.

---

## Nodes

| Node | File | Reads | Writes | Why |
| --- | --- | --- | --- | --- |
| `load_context` | `nodes/context.py` | `request` | `user_context`, `current_plan`, `progress`, `goals` | Only door to history; delegates to the application-layer Context Builder |
| `classify_request` | `nodes/classify.py` | `request` | `classify` | Deterministic intent classification (`ClassifyPolicy`) |
| `goal_analysis` | `nodes/goal_analysis.py` | `goals`, `request` | `goal_analysis`, `tool_results` | Goal → objective + subtasks (`task_decomposer`) |
| `theoretical_analysis` | `nodes/theoretical_analysis.py` | `goals`, `goal_analysis` | `theoretical_analysis` | Theory workload (`workload_estimator`) |
| `user_situation_analysis` | `nodes/user_situation.py` | `theoretical_analysis`, `user_context` | `user_situation`, `predicted_*`, `stress_estimation` | ML numbers are authoritative; LLM only adds `narrative` |
| `plan_generation` | `nodes/plan_generation.py` | drafts context | `plan_draft`, resets `repair_attempts` | Calls `plan_drafter` in INITIAL / ADJUSTMENT / REPLAN mode |
| `rule_validation` | `nodes/validation.py` | `plan_draft`, preferences | `candidate_plan`, `rule_validation`, `rule_violations` | Scheduler places, Rule Engine judges |
| `plan_repair` | `nodes/repair.py` | `rule_violations`, `plan_draft` | `plan_draft`, `repaired_plan`, `candidate_plan`, `repair_attempts` | Bounded deterministic repair, then re-validate |
| `preview` | `nodes/preview.py` | `plan_draft`, `candidate_plan` | `preview`, `user_adjustment`, `adjustment_count` | `interrupt()` + budget enforcement |
| `plan_finalization` | `nodes/finalization.py` | drafts, `candidate_plan` | `final_plan` | Shapes the persisted payload |
| `process_feedback` | `nodes/feedback.py` | `request`, `user_context` | `replan_reason`, `user_adjustment` | Turns a saved check-in into planner input |
| `ml_prediction` | `nodes/prediction.py` | `user_context`, drafts | `ml_prediction`, `tool_results` | Builds `AdjustmentRequest`, calls the predictor |
| `adjustment_router` | `nodes/adjustment_router.py` | `ml_prediction`, `current_plan`, `progress` | `route` | Runs `AdjustmentRouter` and records the decision |
| `micro_adjustment` | `nodes/micro_adjustment.py` | `current_plan`, `ml_prediction` | `plan_draft`, `limit_factor` | Deterministic light replan, no LLM |
| `new_plan` | `nodes/replan.py` | drafts, `candidate_plan` | `final_plan` | Finalises a new version for MICRO/FULL replan |

---

## Conditional edges

| Edge from | Helper (`app/agent/router.py`) | Values |
| --- | --- | --- |
| `rule_validation` | `should_repair` | `"repair"` (violations and budget left) / `"continue"` |
| `preview` | `route_after_preview` | `"revise"` (a `user_adjustment` is set) / `"finalize"` |
| `adjustment_router` | `route_after_adjustment` | `"no_change"` / `"micro_adjust"` / `"full_replan"` |
| `classify_request` | `route_after_classify` | `"initial"` / `"feedback"` / `"replan"` |

These helpers are trivial on purpose: **all policy lives in
`AdjustmentRouter.decide()`**, so adding a routing condition is a one-file
change and stays unit-testable without LangGraph.

### How to add a routing condition

```python
# app/agent/router.py
def _override(self, state) -> tuple[AdjustmentRoute, str] | None:
    ...
    # NEW: escalations are always free once a deadline is close
    if progress and progress.days_remaining <= 2 and progress.completion_rate < 0.5:
        return AdjustmentRoute.FULL_REPLAN, "deadline pressure"
```

Add a unit test in `tests/agent/test_router.py`. The graph itself is unchanged.

---

## Preview / resume mechanics

| Step | Service call | LangGraph call |
| --- | --- | --- |
| generate | `PlanService.generate_preview` | `graph.invoke(state, config={"configurable": {"thread_id": tid}}, context=ctx)` → returns with `__interrupt__` |
| inspect | `PlanGraph.pending_state(tid)` | `graph.get_state(config)` (used for the ownership check) |
| confirm | `PlanService.confirm_plan` | `graph.invoke(Command(resume={"action": "confirm"}), ...)` |
| adjust | `PlanService.adjust_preview` | `graph.invoke(Command(resume={"action": "adjust", "feedback": ...}), ...)` |

The Service never reads or writes LangGraph state directly — `PlannerGraph`
exposes `extract_preview()`, `extract_final_plan()` and `pending_state()`.
