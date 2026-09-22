# Data Flow

Which layer touches the database, and what happens on each request.

Rule: **nodes never touch the database**. `Database → Context Builder → PlanningContext → PlannerState`
is the only path history reaches the agent.

---

## 1. `POST /api/v1/plans/preview`

```
api/v1/plans.py::preview_plan
  └─ PlanService.generate_preview(user_id, PlannerRequest)
       ├─ UserRepository.get_by_id                     [DB read]
       ├─ GoalRepository.create_many + session.commit  [DB WRITE: goals]
       │     → goal_id_map {goal_key(1-based): real goal id}
       └─ PlannerGraph.generate_preview(request, goal_id_map, emit)
            └─ graph A
                 load_context
                   └─ RepoContextBuilder.build()        [DB read only]
                        ├─ users / user_models / task_executions / feedbacks
                        ├─ plans + tasks + goals (current plan snapshot)
                        └─ memory derivers (pure)  → PlanningContext
                 classify_request      (deterministic)
                 goal_analysis         (task_decomposer tool)
                 theoretical_analysis  (workload_estimator tool)
                 user_situation_analysis (task_duration_predictor tool → app/ml)
                 plan_generation       (plan_drafter tool)
                 rule_validation       (scheduler + rule engine tools)
                 [plan_repair loop]
                 preview               ← interrupt() → run PAUSES here
  └─ 202 PreviewResponse{thread_id, preview, goals_persisted}
```

Interesting consequence: **only the goals are persisted**. If the user never
confirms, there is no orphan plan or task. The preview itself lives in the
LangGraph checkpoint.

## 2. `POST /api/v1/plans/preview/{thread_id}/confirm`

```
PlanService.confirm_plan
  ├─ PlannerGraph.pending_state(thread_id)   [checkpoint read]
  │     └─ ownership check: state["user_id"] must equal the caller
  ├─ graph.resume_preview(action="confirm")  [checkpoint read/write]
  │     └─ preview → plan_finalization → final_plan
  └─ _persist_final_plan(user_id, state)     [DB WRITE]
        ├─ previous plan → status = superseded
        ├─ PlanRepository.create  (version = next_version, parent_plan_id)
        ├─ TaskRepository.create_many  (scheduled_date/start/end from candidate_plan)
        ├─ TaskStandardRepository.create_many
        ├─ ReplanEventRepository.create  (only when trigger_source ∈ {replan, micro_adjust})
        └─ session.commit()
  └─ 201 ConfirmResponse{plan}
```

The provisional ids (`order_index + 1`) are resolved here; the persisted tasks get
real primary keys.

## 3. `POST /api/v1/plans/preview/{thread_id}/adjust`

```
PlanService.adjust_preview
  ├─ pending_state → ownership check
  └─ graph.resume_preview(action="adjust", feedback)
        ├─ budget available  → preview again  → 200 with a new preview
        └─ budget exhausted  → plan_finalization → _persist_final_plan
                                            → 200 budget_exhausted=true, final_plan
```

## 4. `POST /api/v1/plans/{plan_id}/feedback`

```
api/v1/feedback.py::submit_feedback
  └─ FeedbackService.submit_feedback
       ├─ PlanRepository.get_by_id                 [DB read + ownership]
       ├─ FeedbackRepository.create + commit       [DB WRITE: feedback]
       ├─ ReplanService.check_eligibility          [DB read: replan_events]
       └─ PlanService.process_feedback_cycle
            ├─ get_plan (rebuild GoalInput from persisted goals)
            └─ graph B
                 load_context   → PlanningContext (now includes the new feedback)
                 process_feedback
                 ml_prediction  → PredictorSet.adjustment → AdjustmentPrediction
                 adjustment_router → AdjustmentRouter.decide → route
                 ├─ NO_CHANGE     : stop (nothing written)
                 ├─ MICRO_ADJUST  : micro_adjustment → rule_validation → new_plan
                 └─ FULL_REPLAN   : goal_analysis … plan_generation → … → new_plan
            └─ if final_plan is not None: _persist_final_plan  [DB WRITE]
  └─ 201 FeedbackSubmitResponse{feedback, replan_triggered, adjustment{route,reasons,…}}
```

## 5. `POST /api/v1/plans/{plan_id}/replan` (manual)

```
api/v1/plans.py::replan
  ├─ ReplanService.check_eligibility        [DB read: per-user cooldown]
  │     └─ not eligible → 409 replan_not_eligible (+ next_available_at)
  └─ PlanService.replan_with_agent
       ├─ get_plan → GoalInput list
       └─ graph B (replan mode: replan_reason set, request.user_note = reason)
            … → adjustment_router → FULL_REPLAN (explicit requirement override)
            … → new_plan
       └─ _persist_final_plan + ReplanEvent    [DB WRITE]
  └─ 201 ReplanResponse{plan_id, old_version, new_version, …}
```

## 6. `PATCH /plans/{plan_id}/tasks/{task_id}` (unchanged)

`PlanService.update_task` updates the task/standards and, when
`completed=true`, writes a `TaskExecution` row — the ML training data asset
(`planned_duration`, `actual_duration`, `completion_rate`, stress before/after,
difficulty, time of day).

---

## What is persisted where

| Data | Table | Written by |
| --- | --- | --- |
| goals | `goals` | `PlanService._persist_goals` (at preview) |
| plan version | `plans` | `PlanService._persist_final_plan` (at confirm / replan) |
| tasks + placement | `tasks` | `PlanService._persist_final_plan` |
| checkable standards | `task_standards` | `PlanService._persist_final_plan` |
| execution facts | `task_executions` | `PlanService.update_task` |
| daily check-in | `feedbacks` | `FeedbackService` |
| why the plan changed | `replan_events` | `PlanService._persist_final_plan` |
| paused preview + agent state | LangGraph `checkpoints*` | checkpointer |

## ML outputs that reach the user

`user_situation_analysis` produces per-task `duration`, `completion`, `stress`
and `time_slot`. `plan_generation` writes them onto each `GeneratedTaskDraft`
(`predicted_duration`, `completion_probability`, `recommended_time_slot`,
`predicted_stress`) and `_persist_final_plan` stores
`tasks.completion_probability` / `tasks.predicted_duration`.

> This is a regression guard: before this refactor the completion prediction was
> computed and then dropped, so every persisted task had
> `completion_probability = 1.0` (the scheduler default). `tests/agent/test_preview_flow.py`
> asserts the predicted value survives.
