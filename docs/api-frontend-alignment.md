# Frontend Contract Alignment

How the backend maps onto `ideas and structures/openapi.frontend.json` (the
frontend's authoritative OpenAPI 3.0.3 spec) after its refactor.

## Coverage

Verified mechanically by diffing our generated OpenAPI against the spec:

```
frontend endpoints: 25   ours: 30
MISSING: (none)
EXTRA:   POST /api/v1/plans/preview                     (now 202 async job)
         POST /api/v1/plans/preview/{thread_id}/adjust  (now 202 async job)
         POST /api/v1/plans/preview/{thread_id}/confirm
         GET  /api/v1/plans/generation/{job_id}          (polling status)
         GET  /api/v1/plans/generation/{job_id}/events    (live SSE)
```

The three "extra" routes are the preview flow, kept **on purpose** so the existing
implementation, tests and `docs/agent/*` stay valid. The frontend's
`decompose`/`confirm` are additive aliases over the same graph.

## What was added

| Endpoint | Status | Behaviour |
| --- | --- | --- |
| `GET /users/me/preferences` | 200 | Effective `SchedulingPreferences` (column → legacy `profile` keys → defaults) |
| `PUT /users/me/preferences` | 200 | Full overwrite on the dedicated column; validates `HH:MM` |
| `GET /users/me/situation/trends?days=2..90` | 200 | Daily energy/stress/efficacy points, `samples`/`min_samples`/`sufficient`, Chinese `drivers` |
| `POST /plans/decompose` | 200 | Multi-goal draft grouped by day (`draft_id`, `days[].tasks[]`), **not persisted** |
| `POST /plans/confirm` | 200 | `{draft_id}` → full `PlanRead`; 404 unknown/expired, 409 already confirmed |
| `GET /plans/{plan_id}/changes` | 200 | Replan events with a per-day diff (`added`/`moved`/`removed`/`summary`/`task_ids`) |
| `GET /goals?status=` | 200 | Goal list; `status=draft` = the frontend's 待拆解清单 |
| `POST /goals` | 201 | Create (with `status: draft` for a pending item) |
| `PATCH /goals/{goal_id}` | 200 | Partial edit |
| `DELETE /goals/{goal_id}` | 204 | 409 when a plan task still references the goal |

`InsightRead` gained `data_sufficiency {samples, min_samples, sufficient}` and
`drivers[]` (both nullable/optional, so existing clients are unaffected).

## 真流式异步任务（preview / adjust 改造）

`POST /plans/preview` 与 `POST /plans/preview/{thread_id}/adjust` 不再是同步长请求，
它们立刻返回 **202** 任务描述符，图在后台线程执行（自己的 DB session），进度通过
SSE 实时推送：

| Endpoint | Status | Behaviour |
| --- | --- | --- |
| `POST /plans/preview` | 202 | `{job_id, status, events_url, status_url}`；不再直接返回 preview |
| `POST /plans/preview/{thread_id}/adjust` | 202 | 同上；body 只需 `{feedback}`（`thread_id` 在 path） |
| `GET /plans/generation/{job_id}` | 200 | 轮询兜底：`{job_id, kind, status, result, error, events}` |
| `GET /plans/generation/{job_id}/events` | 200 | **实时** SSE；逐节点 `event: <node>`，最后 `event: completed`（data 含 `result`） |

- `result` 的形状：`kind="preview"` → 原 `PreviewResponse`；`kind="preview_adjust"` → 原 `AdjustResponse`（含 `final_plan`）。
- SSE 会在 15s 无事件时发送 `: ping` 心跳，防代理断开。
- 前端用 `expo/fetch`（SDK 57 内建流式）+ 手写 SSE 解析；`response.body` 不可用时自动降级为轮询 `status_url`。
- `POST /plans/generate`、`/plans/decompose`、`/plans/confirm` 仍为同步（未改）。

## Decisions taken (confirmed with the product owner)

1. **`decompose`/`confirm` coexist with `/plans/preview*`.** One implementation
   (the preview graph), two entry points. `draft_id` **is** the LangGraph
   `thread_id`, and it doubles as the `agent_runs.run_id` so a draft is traceable.
2. **Adjustment budget = 3** (`AGENT_MAX_PREVIEW_ADJUSTMENTS`).
   `decompose` with a `draft_id` beyond the budget returns **409** with a
   Chinese explanation; the `/plans/preview/{id}/adjust` route keeps its original
   behaviour of finalising the draft (covered by TEST 7).
3. **Preferences live on `users.scheduling_preferences`** (migration
   `d696086158be`) so a wholesale `PATCH /users/me` profile update cannot wipe
   them. `profile` is still read as a legacy fallback.
4. **`POST /plans/generate` now honours its scheduling parameters.** They used to
   be silently dropped (Pydantic `extra="ignore"` — `PlannerRequest` had no such
   fields). Now: sent values win, omitted values fall back to the stored
   preferences. `user_profile` is forwarded as `profile`.

## Deliberately unchanged

- `POST /plans/generate` — still synchronous, `202`, returns the full plan, no
  fake SSE progress.
- `PATCH /tasks/{id}` — `completed: false` stays a **no-op**; un-completing means
  `{"status": "scheduled"}`.
- Feedback → auto-replan below 50% completion, per-user 24 h cooldown, `409` with
  `next_eligible_at`.
- SSE stage names (`goal_analysis` … `plan_repair`, `completed`).
- `GET /plans`, `GET /plans/{id}`, `GET|POST /plans/{id}/feedback`,
  `POST /plans/{id}/replan`, `…/replan/eligibility`, `…/insights`, `/health`,
  `/auth/*`, `/users/me`.

## Field notes worth knowing

| Contract field | Our behaviour |
| --- | --- |
| `DecomposeDraftTask.priority` (1..3) | our `Priority` is 1..4; the decompose mapper clamps `4 → 3` so the contract's range holds |
| `DecomposeDraftTask.source_index` | 0-based index into the request `goals[]` (the graph tracks a 1-based `goal_id`) |
| `DecomposeDraftTask.start_time/end_time` | from the rule-validated scheduler, not from the LLM (the model is never asked for clock times) |
| `PlanChangeRead.days[].summary`, `drivers[]` | Chinese UI copy (the product surface is Chinese) |
| `PlanChangeRead.days[]` diff | derived at read time by comparing the two immutable plan versions — no extra column on `replan_events` |
| `SituationTrendRead.points[].efficacy` | backend-computed `0.6 × execution_weight + 0.4 × recent completion rate`; the frontend preference for `points[].efficacy` now has a value |
| `decompose` with `draft_id` and no `feedback` | treated as "regenerate unchanged": it still consumes one revision round (so it cannot silently finalise the draft) |

## Still open (from `backend-api-gaps-解释版.md`)

| Item | Status |
| --- | --- |
| 真 LLM 拆解 | configuration-side (`LLM_PROVIDER` + key); the code path is wired |
| 月视图 / longer horizon | **not implemented** — plans still span ~14 days |
| 目标草稿跨设备 | done via `/goals` + `status: draft` |
| 「效能」定义 | backend now defines it (formula above) |
| 重排能记录「为什么」 | `reason` + `trigger_type` returned; the day-level diff is derived |

## How to verify

```bash
uv run pytest tests/api/test_frontend_contract.py -v   # 16 contract tests
uv run pytest                                          # 172 tests
uv run alembic current                                 # d696086158be (head)
uv run python scripts/evaluate_predictors.py           # prediction scoring
```
