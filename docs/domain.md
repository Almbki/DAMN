# Domain Model

All entities live in `app/domain/models/` and are pure Pydantic v2 models
(`ConfigDict(from_attributes=True)`), independent of SQLAlchemy. The ORM mirror
lives in `app/infrastructure/database/models/`; repositories convert between the
two.

---

## 1. Entities

### User — `app/domain/models/user.py`

| Field | Type | Notes |
| --- | --- | --- |
| `id` | `int \| None` | PK |
| `email` | `EmailStr` | unique |
| `password_hash` | `str` | PBKDF2-HMAC-SHA256 (`core/security.py`) |
| `display_name` | `str \| None` | |
| `execution_weight` | `float` 0..1 | self-reported "execution ability" prior |
| `profile` | `dict` | available hours, sleep schedule, preferences |
| `created_at` | `datetime` | |

### Goal — `goal.py`

| Field | Type | Notes |
| --- | --- | --- |
| `id`, `user_id` | `int` | |
| `title`, `description` | `str`, `str \| None` | |
| `goal_type` | `GoalType` | long_term / short_term / project / habit / other |
| `deadline` | `datetime \| None` | hard upper bound for scheduling |
| `priority` | `Priority` | int enum 1..4 |
| `status` | `GoalStatus` | active / completed / archived / cancelled |
| `estimated_minutes` | `int \| None` | user-supplied workload |
| `options` | `dict` | `{subject, task_type}` from the request |
| `created_at` | `datetime` | |

### Plan — `plan.py`

| Field | Type | Notes |
| --- | --- | --- |
| `id`, `user_id` | `int` | |
| `version` | `int` | 1, 2, 3 … unique per user |
| `status` | `PlanStatus` | draft / active / superseded / completed / archived |
| `title` | `str \| None` | |
| `start_date`, `end_date` | `date` | scheduling horizon |
| `parent_plan_id` | `int \| None` | previous version |
| `confidence` | `float` 0..1 | mean of pipeline confidences |
| `created_at` | `datetime` | |

### Task — `task.py`

| Field | Type | Notes |
| --- | --- | --- |
| `id`, `plan_id` | `int` | |
| `goal_id`, `parent_task_id` | `int \| None` | |
| `title`, `description` | `str`, `str \| None` | |
| `estimated_duration` | `int` | minutes (theoretical / user estimate) |
| `predicted_duration` | `int \| None` | minutes (ML prediction) |
| `cognitive_load` | `CognitiveLoad` | high / medium / low / restorative |
| `priority` | `Priority` | |
| `scheduled_date`, `start_time`, `end_time` | `date \| None`, `time \| None` | output of the Scheduler |
| `status` | `TaskStatus` | pending / scheduled / in_progress / completed / skipped / failed |
| `completion_probability` | `float \| None` | ML prediction 0..1 |
| `is_flexible` | `bool` | may be dropped by repair |
| `order_index` | `int` | stable ordering; provisional id = `order_index + 1` |

### TaskStandard — `task_standard.py`

Quantifiable "definition of done". `id`, `task_id`, `description`,
`estimated_duration` (minutes), `completed`, `order_index`.

### TaskExecution — `execution.py` (the ML data asset)

| Field | Type | Notes |
| --- | --- | --- |
| `id`, `task_id`, `user_id` | `int` | |
| `planned_duration`, `actual_duration` | `int` | minutes |
| `completion_rate` | `float` 0..1 | |
| `started_at`, `finished_at` | `datetime \| None` | |
| `difficulty_feedback` | `int \| None` 1..5 | self report |
| `stress_before`, `stress_after` | `int \| None` 0..10 | self report |
| `failure_reason` | `str \| None` | |
| `time_of_day` | `TimeOfDay \| None` | |
| `completed` | `bool` | |
| `created_at` | `datetime` | |

### Feedback — `feedback.py` (daily check-in)

`id`, `user_id`, `plan_id`, `date`, `completion_rate` (0..1), `stress_level`
(0..10), `energy_level` (0..10), `delay_reason`, `free_text`, `sleep_hours`,
`dominant_time_of_day`, `created_at`.

### UserModel — `user_model.py`

| Field | Type | Notes |
| --- | --- | --- |
| `id`, `user_id` | `int` | one row per user |
| `model_version` | `str` | e.g. `statistical-v0` |
| `duration_factors` | `dict[str, float]` | per load bucket; `predicted = theoretical × factor` |
| `completion_probability` | `dict[str, float]` | per load bucket |
| `stress_response` | `dict[str, float]` | mean stress delta per load bucket |
| `preferred_time_slots` | `dict[str, str]` | per load bucket |
| `sample_size` | `int` | executions behind the factors (confidence proxy) |
| `updated_at` | `datetime` | |

### ReplanEvent — `replan_event.py`

| Field | Type | Notes |
| --- | --- | --- |
| `id`, `plan_id` | `int` | plan that was replanned into |
| `trigger_type` | `ReplanTriggerType` | manual / feedback_triggered / scheduled / system |
| `reason` | `str \| None` | |
| `old_version`, `new_version` | `int` | |
| `changed_tasks` | `list[int]` | task ids whose schedule changed |
| `created_at` | `datetime` | |

---

## 2. Enums — `enums.py`

| Enum | Values |
| --- | --- |
| `GoalType` | long_term, short_term, project, habit, other |
| `GoalStatus` | active, completed, archived, cancelled |
| `PlanStatus` | draft, active, superseded, completed, archived |
| `TaskStatus` | pending, scheduled, in_progress, completed, skipped, failed |
| `CognitiveLoad` | high, medium, low, restorative |
| `Priority` | int: LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4 |
| `ReplanTriggerType` | manual, feedback_triggered, scheduled, system |
| `ViolationSeverity` | hard, soft |
| `TimeOfDay` | morning, afternoon, evening, night |
| `LoadLevel` | low, moderate, high, overloaded |

---

## 3. Hard-constraint Rule Engine — `app/domain/rules/`

```python
Rule.violate(schedule, context) -> list[RuleViolation]
```

```json
{ "rule": "...", "severity": "hard", "task_ids": [], "message": "...", "code": "..." }
```

`RuleEngine.validate(schedule, context)` runs all rules; `hard_violations()`
filters `severity == hard`; `is_valid()` is `not hard_violations()`.

### The 7 constraints

| # | Constraint | Module | Rule name | Code |
| --- | --- | --- | --- | --- |
| 1 | High-cognitive tasks must not be consecutive (≥30 min gap or a non-high task between) | `cognitive_load.py` | `high_cognitive_not_consecutive` | `high_cognitive_consecutive` |
| 1b | ≤ `high_cognitive_max_per_day` high-cognitive tasks per day | `cognitive_load.py` | `high_cognitive_not_consecutive` | `high_cognitive_daily_max` |
| 2 | Math and algorithm must not share a day | `same_day_conflict.py` | `same_day_conflict` | `same_day_conflict` |
| 3 | Daily total ≤ `daily_limit_minutes` | `daily_limit.py` | `daily_limit` | `daily_limit` |
| 4 | Buffer ≥ `buffer_minutes` between tasks (overlaps flagged) | `buffer_time.py` | `buffer_time` | `insufficient_buffer` |
| 5 | Daily total ≤ `available_minutes_per_day` and inside `[day_start, day_end]` | `daily_limit.py` | `available_time` | `available_time` / `outside_available_window` |
| 6 | Not scheduled after the task's deadline | `deadline.py` | `deadline` | `deadline_exceeded` |
| 7 | Completed tasks must not be re-scheduled | `completed_tasks.py` | `completed_task_rescheduled` | `completed_task_rescheduled` |

`RuleContext` carries everything rules need beyond the schedule: limits, window,
`task_subjects` (`{task_id: "math"}`), `task_deadlines` (`{task_id: date}`),
`completed_task_ids`, `conflicting_subject_pairs` (default `[("math","algorithm")]`).

---

## 4. Scheduler — `app/domain/scheduling/scheduler.py`

The Scheduler is **heuristic, deterministic and LLM-free**. It produces a
*candidate*; the Rule Engine remains the authority.

```python
Scheduler(config: SchedulerConfig | None).schedule(tasks: list[Task], context: RuleContext) -> CandidateSchedule
```

Algorithm:

1. Skip tasks whose id is in `context.completed_task_ids`.
2. Sort by priority desc → deadline-having first, deadline asc → high cognitive
   first → `order_index`.
3. Horizon: `start = today`, `end = max(latest deadline, start + 14 days)`.
4. Greedily place each task on the earliest feasible day:
   - remaining capacity = `min(daily_limit_minutes, available_minutes_per_day)`
   - buffer to neighbours ≥ `buffer_minutes`
   - high-cognitive daily cap
   - no subject conflict with already-placed tasks that day
   - inside `[day_start, day_end]` on `slot_minutes` boundaries
   - ≥ 30 min spacing from neighbouring high-cognitive tasks
5. `duration_minutes = predicted_duration or estimated_duration`;
   `completion_probability` defaults to `1.0`.
6. Unplaceable tasks → `unscheduled_task_ids`.

`SchedulerConfig`: `day_start=08:00`, `day_end=22:00`, `slot_minutes=15`,
`max_high_cognitive_per_day=2` (informational — `RuleContext` is authoritative),
`default_horizon_days=14`.

`CandidateSchedule` helpers: `tasks_on(day)`, `daily_minutes()`, `days()`.

---

## 5. Plan versioning semantics

- Every generation/replan creates a **new** `Plan` row; old rows are never mutated
  except for `status = superseded`.
- `version = PlanRepository.next_version(user_id)` (max + 1).
- `parent_plan_id` links v(n+1) → v(n).
- `ReplanEvent` records `trigger_type`, `reason`, `old_version`, `new_version`,
  `changed_tasks`.
- Replan copies only non-completed tasks (`status != completed/skipped`).

---

## 6. Validation entry point

`PATCH /plans/{plan_id}/tasks/{task_id}` with `completed=true`:

1. `PlanService.update_task` updates the task (and its standards),
2. sets `status = completed`,
3. writes a `TaskExecution` row with `planned_duration`
   (`predicted_duration or estimated_duration`) and any reported actuals.

This is the write path that feeds the ML layer.
