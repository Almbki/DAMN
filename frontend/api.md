# API Reference

Base path: `/api/v1` · Interactive docs: `/docs` (Swagger UI), `/redoc` (ReDoc),
schema: `/openapi.json`.

All errors use the same envelope:

```json
{ "code": "not_found", "message": "plan not found", "detail": null }
```

| Error | Status | `code` |
| --- | --- | --- |
| `NotFoundError` | 404 | `not_found` |
| `PermissionDeniedError` | 403 | `permission_denied` |
| `AuthenticationError` | 401 | `unauthorized` |
| `ConflictError` | 409 | `conflict` |
| `ReplanNotEligibleError` | 409 | `replan_not_eligible` |
| `DomainValidationError` | 422 | `validation_error` |
| Pydantic validation | 422 | FastAPI default body |

Authentication: `Authorization: Bearer <JWT>` (`HTTPBearer`). Obtain the token
from `POST /auth/login`.

OpenAPI tags: `system`, `auth`, `users`, `plans`, `feedback`, `tasks`, `insights`.

---

## Endpoint summary

| Method | Path | Auth | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/health` | no | 200 `HealthResponse` | — |
| POST | `/auth/register` | no | 201 `UserRead` | 409 |
| POST | `/auth/login` | no | 200 `TokenResponse` | 401 |
| GET | `/users/me` | yes | 200 `UserRead` | 401 |
| PATCH | `/users/me` | yes | 200 `UserRead` | 401 |
| POST | `/plans/generate` | yes | 202 `PlanGenerateResponse` | 401, 422 |
| GET | `/plans/generation/{job_id}/events` | yes | 200 `text/event-stream` | 401, 404 |
| GET | `/plans` | yes | 200 `list[PlanListItem]` | 401 |
| GET | `/plans/{plan_id}` | yes | 200 `PlanRead` | 401, 403, 404 |
| PATCH | `/plans/{plan_id}/tasks/{task_id}` | yes | 200 `TaskRead` | 401, 403, 404 |
| POST | `/plans/{plan_id}/feedback` | yes | 201 `FeedbackSubmitResponse` | 401, 403, 404 |
| GET | `/plans/{plan_id}/feedback` | yes | 200 `list[FeedbackRead]` | 401, 403, 404 |
| POST | `/plans/{plan_id}/replan` | yes | 201 `ReplanResponse` | 401, 403, 404, 409 |
| GET | `/plans/{plan_id}/replan/eligibility` | yes | 200 `ReplanEligibilityRead` | 401, 403, 404 |
| GET | `/plans/{plan_id}/insights` | yes | 200 `InsightRead` | 401, 403, 404 |

---

## System

### `GET /health`

```json
{ "status": "ok", "app": "AI Adaptive Task Planner", "version": "0.1.0", "environment": "development" }
```

---

## Auth

### `POST /auth/register` → 201

Request `RegisterRequest`:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `email` | EmailStr | yes | unique |
| `password` | str | yes | 8–128 chars |
| `display_name` | str \| null | no | |
| `execution_weight` | float 0..1 | no | default `0.5` |
| `profile` | object | no | available time, sleep schedule, … |

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"a@b.com","password":"password123","display_name":"Ann"}'
```

Response `UserRead`:

```json
{
  "id": 1,
  "email": "a@b.com",
  "display_name": "Ann",
  "execution_weight": 0.5,
  "profile": {},
  "created_at": "2026-09-19T11:38:56.269Z"
}
```

### `POST /auth/login` → 200

```json
{ "email": "a@b.com", "password": "password123" }
```

```json
{ "access_token": "<jwt>", "token_type": "bearer", "expires_in": 604800 }
```

---

## Users

### `GET /users/me` → 200 `UserRead`

### `PATCH /users/me` → 200 `UserRead`

Body `UserUpdate` (all optional): `display_name`, `execution_weight` (0..1), `profile`.

---

## Plans

### `POST /plans/generate` → 202

Request `PlanGenerateRequest`:

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `goals` | `list[GoalCreate]` | — | min 1 |
| `start_date` / `end_date` | date | today / today+13 | horizon |
| `plan_title` | str \| null | null | |
| `available_minutes_per_day` | int 1..1440 | 480 | constraint 5 |
| `daily_limit_minutes` | int 1..1440 | 300 | constraint 3 |
| `buffer_minutes` | int 0..120 | 15 | constraint 4 |
| `high_cognitive_max_per_day` | int 1..10 | 2 | constraint 1b |
| `user_profile` | object | `{}` | |
| `execution_weight` | float \| null | user value | |

`GoalCreate`: `title` (required), `description`, `goal_type`
(`long_term|short_term|project|habit|other`), `deadline` (ISO datetime),
`priority` (int `1..4`), `estimated_minutes`, `subject`, `task_type`.

```bash
curl -X POST http://localhost:8000/api/v1/plans/generate \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "goals": [{"title":"复习高数极限","description":"看课\n做例题\n做练习","subject":"math","estimated_minutes":120,"priority":3}],
    "plan_title":"My Plan"
  }'
```

Response `PlanGenerateResponse`:

```json
{
  "job_id": "3f1c…",
  "status": "completed",
  "plan_id": 1,
  "events_url": "/api/v1/plans/generation/3f1c…/events",
  "plan": { "id": 1, "version": 1, "status": "active", "tasks": [ /* TaskRead */ ], "goals": [ /* GoalRead */ ] }
}
```

### `GET /plans/generation/{job_id}/events` → 200 SSE

```
event: goal_analysis
data: {"node":"goal_analysis","stage":"goal_analysis","status":"completed","summary":"goal_analysis: 1 goal(s), confidence=0.60","payload":{},"progress":0.125,"timestamp":"..."}

event: theoretical_analysis
data: {...}

event: user_situation_analysis
data: {...}

event: plan_generation
data: {...}

event: rule_validation
data: {...}

event: plan_repair          # only when repair ran
data: {...}

event: completed
data: {"plan_id":1,"status":"completed","job_id":"3f1c…"}
```

Render with `EventSource`, e.g. in React Native use an SSE polyfill and listen
for the six stage names plus `completed`.

### `GET /plans` → 200 `list[PlanListItem]`

`PlanListItem`: `id`, `version`, `status`, `title`, `start_date`, `end_date`,
`confidence`, `created_at`, `task_count`, `completed_count`.

### `GET /plans/{plan_id}` → 200 `PlanRead`

```json
{
  "id": 1, "user_id": 1, "version": 1, "status": "active",
  "title": "My Plan", "start_date": "2026-09-19", "end_date": "2026-10-02",
  "parent_plan_id": null, "confidence": 0.52, "created_at": "...",
  "tasks": [{
    "id": 1, "plan_id": 1, "goal_id": 1, "title": "复习高数极限",
    "estimated_duration": 120, "predicted_duration": 174,
    "cognitive_load": "high", "priority": 3,
    "scheduled_date": "2026-09-19", "start_time": "08:00:00", "end_time": "10:54:00",
    "status": "scheduled", "completion_probability": 0.71,
    "standards": [{"id": 1, "description": "看课", "estimated_duration": 30, "completed": false, "order_index": 0}]
  }],
  "goals": [{"id": 1, "title": "复习高数极限", "goal_type": "short_term", "priority": 3, "status": "active"}]
}
```

### `PATCH /plans/{plan_id}/tasks/{task_id}` → 200 `TaskRead`

Body `TaskUpdateRequest` (all optional): `status`
(`pending|scheduled|in_progress|completed|skipped|failed`), `completed` (bool),
`actual_duration` (int), `difficulty_feedback` (1..5), `stress_before`,
`stress_after` (0..10), `failure_reason`, `started_at`, `finished_at`,
`standard_updates` (`[{ "id": 1, "completed": true }]`).

`completed: true` also writes a `TaskExecution` row (ML data asset).

```json
{ "completed": true, "actual_duration": 90, "difficulty_feedback": 4, "stress_after": 6 }
```

---

## Feedback

### `POST /plans/{plan_id}/feedback` → 201

Request `FeedbackCreate`: `date` (required), `completion_rate` (0..1),
`stress_level` (0..10), `energy_level` (0..10), `delay_reason`, `free_text`,
`sleep_hours` (0..24), `dominant_time_of_day`.

Response `FeedbackSubmitResponse`:

```json
{
  "feedback": { "id": 1, "plan_id": 1, "date": "2026-09-19", "completion_rate": 0.4, "...": "..." },
  "replan_triggered": true,
  "replan_plan_id": 2,
  "replan_eligibility": { "eligible": false, "reason": "cooldown active until ...", "next_eligible_at": "...", "last_replan_at": "...", "cooldown_hours": 24 }
}
```

Auto-replan fires when `completion_rate < 0.5` **and** the user is eligible.
`replan_plan_id` is the newly created plan version.

### `GET /plans/{plan_id}/feedback` → 200 `list[FeedbackRead]`

---

## Replan

### `GET /plans/{plan_id}/replan/eligibility` → 200

```json
{ "eligible": true, "reason": "no previous replan", "next_eligible_at": null, "last_replan_at": null, "cooldown_hours": 24 }
```

Cooldown is a **per-user** rate limit (`SCHEDULER_MIN_REPLAN_INTERVAL_HOURS`,
default 24 h). After any replan, every eligibility check returns `eligible: false`
until it elapses.

### `POST /plans/{plan_id}/replan` → 201

Request `ReplanRequest`: `trigger_type` (`manual|feedback_triggered|scheduled|system`),
`reason`, `from_date`.

```json
{
  "plan_id": 2, "old_version": 1, "new_version": 2,
  "changed_task_ids": [3, 4], "reason": "too heavy", "trigger_type": "manual"
}
```

- Creates a new `Plan` version (never overwrites), marks the old one `superseded`,
  records a `ReplanEvent`, copies + re-schedules all non-completed tasks.
- Returns **409** `replan_not_eligible` while the cooldown is active.

---

## Insights

### `GET /plans/{plan_id}/insights` → 200 `InsightRead`

```json
{
  "plan_id": 1, "total_tasks": 3, "completed_tasks": 1, "completion_rate": 0.333,
  "total_planned_minutes": 300, "total_actual_minutes": 90,
  "avg_stress": 8.0, "avg_energy": 3.0, "high_cognitive_minutes": 120,
  "predicted_vs_actual_ratio": 0.3,
  "cognitive_load_breakdown": { "high": 1, "medium": 2 },
  "daily": [{ "date": "2026-09-19", "total_tasks": 2, "completed_tasks": 1, "completion_rate": 0.5, "planned_minutes": 180 }],
  "recommendations": ["Completion rate is low - consider reducing daily load or replanning."]
}
```

`predicted_vs_actual_ratio` = Σ actual ÷ Σ planned over executions; `> 1.3`
means the duration factor is too low, `< 0.7` too high.

---

## Status code conventions

- `202` for `POST /plans/generate` (accepts work, returns a job).
- `201` for resource creation (`register`, `feedback`, `replan` → new version).
- `200` for reads and patches.
- `401` missing/invalid bearer token, `403` resource owned by another user,
  `404` unknown resource, `409` conflicts (email, cooldown), `422` validation.
