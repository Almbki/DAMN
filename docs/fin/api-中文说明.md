# 后端接口中文说明

配套文件：`docs/design/openapi.frontend.json`（OpenAPI 3.0.3，可直接导入 Swagger / Postman / Apifox
或生成客户端）。

这里是**每个接口的作用、谁在用、收发什么**的中文说明。标记：

- **[已有]** 后端现在就能用。
- **[待新增]** 前端已经按契约写好，等后端补接口。

---

## 0. 通用约定

| 项 | 值 |
| --- | --- |
| 服务器 | `http://192.168.9.67:8000` |
| API 前缀 | `/api/v1` |
| 健康检查 | 根路径 `/health`（**不在** `/api/v1` 下） |
| 认证 | 除 `/health`、`/auth/*` 外都要 `Authorization: Bearer <JWT>` |
| 超时 | 前端 30s（后端偶发卡顿） |
| 错误体 | `{ "code": string, "message": string, "detail": any \| null }` |

常见状态码：`200` 读/改成功 · `201` 创建 · `202` 生成计划 · `204` 删除成功 ·
`401` 未认证 · `403` 别人的资源 · `404` 不存在 · `409` 冲突（邮箱重复 / 重排冷却）·
`422` 参数校验失败。

日期格式 `YYYY-MM-DD`；时间格式 `HH:MM:SS`；时间戳用 ISO 8601。

---

## 1. 一组速查表

| 方法 | 路径 | 作用 | 状态 |
| --- | --- | --- | --- |
| GET | `/health` | 健康检查 | 已有 |
| POST | `/api/v1/auth/register` | 注册 | 已有 |
| POST | `/api/v1/auth/login` | 登录拿 JWT | 已有 |
| GET | `/api/v1/users/me` | 读当前用户 | 已有 |
| PATCH | `/api/v1/users/me` | 改昵称 / 执行权重 / profile | 已有 |
| GET | `/api/v1/users/me/preferences` | 读排程偏好 | **待新增** |
| PUT | `/api/v1/users/me/preferences` | 存排程偏好 | **待新增** |
| GET | `/api/v1/users/me/situation/trends` | 画像趋势 | **待新增** |
| GET | `/api/v1/plans` | 计划列表 | 已有 |
| POST | `/api/v1/plans/generate` | 目标 → 计划（同步落库） | 已有 |
| POST | `/api/v1/plans/decompose` | 批量拆解 → 预览草稿 | **待新增** |
| POST | `/api/v1/plans/confirm` | 确认草稿落库 | **待新增** |
| GET | `/api/v1/plans/{plan_id}` | 计划详情 | 已有 |
| GET | `/api/v1/plans/{plan_id}/changes` | 计划变更记录 | **待新增** |
| PATCH | `/api/v1/plans/{plan_id}/tasks/{task_id}` | 改任务状态 | 已有 |
| GET | `/api/v1/plans/{plan_id}/feedback` | 反馈历史 | 已有 |
| POST | `/api/v1/plans/{plan_id}/feedback` | 提交每日反馈 | 已有 |
| POST | `/api/v1/plans/{plan_id}/replan` | 手动重排 | 已有 |
| GET | `/api/v1/plans/{plan_id}/replan/eligibility` | 重排冷却资格 | 已有 |
| GET | `/api/v1/plans/{plan_id}/insights` | 计划分析 | 已有 |
| GET | `/api/v1/plans/generation/{job_id}/events` | 生成进度 SSE | 已有（前端暂未用） |
| GET | `/api/v1/goals` | 目标 / 待拆解清单 | **待新增** |
| POST | `/api/v1/goals` | 新建目标 / 待拆解项 | **待新增** |
| PATCH | `/api/v1/goals/{goal_id}` | 编辑目标 / 待拆解项 | **待新增** |
| DELETE | `/api/v1/goals/{goal_id}` | 删除目标 / 待拆解项 | **待新增** |

---

## 2. system

### GET `/health` [已有]
**作用**：确认后端在线。
**谁在用**：前端启动时的连接检查，以及运维探活。
**返回**：`{ status, app, version, environment }`。

---

## 3. auth

### POST `/api/v1/auth/register` [已有]
**作用**：邮箱 + 密码注册。
**请求**：`email`（必填）、`password`（8–128 位，必填）、`display_name?`、
`execution_weight?`（0–1，默认 0.5）、`profile?`。
**返回 201**：`UserRead`。
**注意**：邮箱已存在返回 **409**；前端遇到 409 会转去登录。

### POST `/api/v1/auth/login` [已有]
**作用**：登录换取 JWT。
**请求**：`email`、`password`。
**返回 200**：`{ access_token, token_type, expires_in }`。
**注意**：前端把 `access_token` 放进后续请求的 `Authorization` 头；密码错误返回 **401**。

---

## 4. users（用户 / 偏好 / 画像趋势）

### GET `/api/v1/users/me` [已有]
**作用**：读取当前用户。
**谁在用**：设置页「账号信息」、画像页显示执行权重。
**返回**：`UserRead`：`id`、`email`、`display_name`、`execution_weight`、
`profile`（自由 JSON）、`created_at`。

### PATCH `/api/v1/users/me` [已有]
**作用**：修改昵称 / 执行权重 / profile。
**请求**（都可选）：`display_name`、`execution_weight`（0–1）、`profile`。
**返回**：`UserRead`。
**注意**：`profile` 是**全量覆盖**语义，前端会先合并整份再提交；后端不要假设只收到变化字段。

### GET `/api/v1/users/me/preferences` [待新增]
**作用**：读取排程偏好，让「设置一次就一直生效」跨设备成立。
**谁在用**：设置页「排程偏好」＋画像二级页「基础档案」。
**返回**：`SchedulingPreferences`（见字段字典）。

### PUT `/api/v1/users/me/preferences` [待新增]
**作用**：整体保存排程偏好。
**请求 / 返回**：`SchedulingPreferences`。
**关键要求**：`POST /plans/generate` 在请求体**没传**这四个数时，应**回退读取本偏好**，
否则前端仍得每次重传，"设一次生效"不成立。

### GET `/api/v1/users/me/situation/trends` [待新增]
**作用**：画像一级页的曲线与判断依据。
**查询参数**：`days`（默认 14，2–90）。
**返回**：`SituationTrendRead`：
- `points[]`：每天 `{ date, energy(0–10), stress(0–10), efficacy(0..1) }`，缺的那天字段为 `null`。
- `samples` / `min_samples` / `sufficient`：数据够不够。
- `drivers[]`：系统为什么这么判断（人话句子）。
**注意**：后端目前**没有** efficacy（效能）字段；前端暂时用
`0.6 × execution_weight + 0.4 × 近 14 天完成率` 兜底。若后端定义了自己的效能，以 `points[].efficacy` 为准。

---

## 5. plans（计划）

### GET `/api/v1/plans` [已有]
**作用**：列出当前用户的计划版本。
**谁在用**：前端启动时找 `status === "active"` 的那一版。
**返回**：`PlanListItem[]`：`id`、`version`、`status`、`title`、`start_date`、`end_date`、
`confidence`、`created_at`、`task_count`、`completed_count`。

### POST `/api/v1/plans/generate` [已有]
**作用**：目标 → 计划，**同步**生成并落库。
**谁在用**：目标页「拆解确认」在后端 draft 接口就绪前的回退路径；以及旧的快速生成。
**请求**：`goals[]`（必填，≥1）、`start_date?`、`end_date?`、`plan_title?`、
`available_minutes_per_day?`（默认 480）、`daily_limit_minutes?`（默认 300）、
`buffer_minutes?`（默认 15）、`high_cognitive_max_per_day?`（默认 2）、`user_profile?`、`execution_weight?`。
**返回 202**：`PlanGenerateResponse`（`job_id`、`status`、`plan_id`、`events_url`、`plan`）。
**注意**：返回里**直接带完整 plan**，前端**不做 SSE 假进度**。

### POST `/api/v1/plans/decompose` [待新增]
**作用**：把目标页攒好的**多条**待拆解任务，交给后端智能体，返回一份**不落库**的草稿（按天分组）。
**谁在用**：目标页「拆解」按钮 → 只读预览弹窗。
**请求**：
- `goals[]`（≥1）：每条 `{ title, priority(1–3), deadline?, notes }`。
- `draft_id?`：**重新生成**时带同一个 draft_id。
- `feedback?`：用户对上一版预览的意见（如「晚点做」「少一点」「挪到周末」）。
**返回 200**：`{ draft_id, days: [{ date, tasks: [{ title, priority, estimated_minutes, start_time?, end_time?, source_index? }] }] }`。
**核心要求**：真正的"理解多条大目标 → 拆成每天任务"由后端接**智能体**完成
（现在后端是确定性启发式 + MockLLM，不是真 LLM）。

### POST `/api/v1/plans/confirm` [待新增]
**作用**：用户点「就先这样」，把草稿落成正式计划。
**请求**：`{ draft_id }`。
**返回 200**：`PlanRead`（前端直接应用，无需再拉取）。
**注意**：草稿不存在 / 已过期 → 404；重复确认 → 409。

### GET `/api/v1/plans/{plan_id}` [已有]
**作用**：计划详情，含该版本全部任务与该计划涉及的目标。
**谁在用**：待办时间轴、按目标分组。
**返回**：`PlanRead`。
**注意**：`tasks[].priority`、`start_time`、`end_time` 被时间轴使用，请给出真实档位。

### GET `/api/v1/plans/{plan_id}/changes` [待新增]
**作用**：待办右上角「计划变更」——系统改了**未来哪几天**、每天加了/挪了/删了几条、为什么。
**背景**：反馈完成率 < 50% 时后端会**自动重排**（未完成任务重新排期），用户没主动改，
需透明化。
**返回**：`PlanChangeRead[]`：`trigger_type`、`reason`、`old_version`、`new_version`、
`created_at`、`days[]`（`date`、`added`、`moved`、`removed`、`summary`、`task_ids?`）。
**实现要点**：服务端在 `ReplanService.replan` 已能拿到旧/新 `(scheduled_date, start_time, end_time)`，
把 **date diff** 一起写入 `ReplanEvent` 即可。

### POST `/api/v1/plans/{plan_id}/replan` [已有]
**作用**：手动重排，生成新版本（不可变，旧版标 `superseded`）。
**请求**：`trigger_type?`、`reason?`、`from_date?`。
**返回 201**：`{ plan_id, old_version, new_version, changed_task_ids[], reason, trigger_type }`。
**注意**：冷却中返回 **409**。

### GET `/api/v1/plans/{plan_id}/replan/eligibility` [已有]
**作用**：查询能否重排（per-user 24h 冷却）。
**返回**：`{ eligible, reason, next_eligible_at?, last_replan_at?, cooldown_hours }`。
**谁在用**：提交反馈后，若未触发重排且 `eligible=false`，前端提示 `next_eligible_at`。

### GET `/api/v1/plans/generation/{job_id}/events` [已有]
**作用**：生成进度的 SSE 事件流。
**事件名**（与图节点同名）：`goal_analysis`、`theoretical_analysis`、`user_situation_analysis`、
`plan_generation`、`rule_validation`、`plan_repair`，外加 `completed`。
**注意**：当前前端走同步 generate，暂不使用；保留契约。

---

## 6. tasks

### PATCH `/api/v1/plans/{plan_id}/tasks/{task_id}` [已有]
**作用**：改任务状态 / 记录执行信息。
**谁在用**：待办勾选完成、跳过。
**请求**（都可选）：`status`、`completed`、`actual_duration`、`difficulty_feedback`、
`stress_before`、`stress_after`、`failure_reason`、`started_at`、`finished_at`、`standard_updates`。
**返回**：`TaskRead`。
**关键约定**：
- 勾选完成：`{ "completed": true }`（会写一条 `TaskExecution`）。
- **取消完成**：必须 `{ "status": "scheduled" }`；`{ "completed": false }` 是 **no-op**。
- 跳过：`{ "status": "skipped" }`。

---

## 7. feedback（反馈）

### GET `/api/v1/plans/{plan_id}/feedback` [已有]
**作用**：当前计划的反馈历史（可给画像趋势兜底）。
**返回**：`FeedbackRead[]`。

### POST `/api/v1/plans/{plan_id}/feedback` [已有]
**作用**：提交每日反馈。
**谁在用**：待办底部「写今日反馈」。
**请求**：`date`（必填）、`completion_rate`（0–1）、`stress_level`（0–10）、`energy_level`（0–10）、
`delay_reason?`、`free_text?`、`sleep_hours?`、`dominant_time_of_day?`。
**返回 201**：`FeedbackSubmitResponse`：
`feedback`、`replan_triggered`、`replan_plan_id?`、`replan_eligibility?`。
**关键逻辑**：`completion_rate < 0.5` 且不在冷却内 → 自动重排，返回 `replan_triggered=true`
与新 `replan_plan_id`（新版本可能 0 任务）。冷却中 → `replan_eligibility.eligible=false` 并给
`next_eligible_at`。

---

## 8. insights（分析）

### GET `/api/v1/plans/{plan_id}/insights` [已有]
**作用**：计划完成率、计划/实际时长、认知负荷、每日完成、建议等。
**谁在用**：画像页部分数据、内部统计。
**返回**：`InsightRead`，字段见字段字典。
**建议新增（画像用，可选）**：`data_sufficiency { samples, min_samples, sufficient }` 与
`drivers: string[]`。

---

## 9. goals（目标 / 待拆解清单）[全部待新增]

前端目标页现在是「待拆解清单 + 两个悬浮按钮」，清单目前只存在前端内存，刷新即丢。
若要跨设备/刷新保留，需要这组接口。

### GET `/api/v1/goals` [待新增]
**作用**：列出目标；`?status=draft` 取"等待拆解"的项。
**返回**：`GoalDetailRead[]`。

### POST `/api/v1/goals` [待新增]
**作用**：新建目标；建待拆解项时传 `status: "draft"`。
**请求**：`title`（必填）、`description?`（对应"补充"）、`goal_type?`、`deadline?`、
`priority?`（1–4）、`estimated_minutes?`、`subject?`、`task_type?`、`status?`。
**返回 201**：`GoalDetailRead`。

### PATCH `/api/v1/goals/{goal_id}` [待新增]
**作用**：编辑目标/待拆解项（名称、优先级、截止、补充、状态）。
**请求/返回**：`GoalUpdate` / `GoalDetailRead`。

### DELETE `/api/v1/goals/{goal_id}` [待新增]
**作用**：删除；成功 **204**。

---

## 10. 字段字典（关键模型）

### UserRead
`id` · `email` · `display_name` · `execution_weight`(0–1，执行权重) · `profile`(自由 JSON) · `created_at`

### SchedulingPreferences
`available_minutes_per_day`(每日可投入，分) · `daily_limit_minutes`(单日上限，分) ·
`buffer_minutes`(任务间缓冲，分) · `high_cognitive_max_per_day`(高认知上限，条) ·
`sleep_start`/`sleep_end`(`HH:MM`)

### TaskRead（时间轴会用到加粗的字段）
`id` · `plan_id` · `goal_id` · `parent_task_id` · `title` · `description` ·
`estimated_duration`(预计分钟) · `predicted_duration` · `cognitive_load`(low/medium/high/restorative) ·
**`priority`**(1 低 / 2 中 / ≥3 高) · **`scheduled_date`** · **`start_time`** · **`end_time`** ·
`status`(pending/scheduled/in_progress/completed/skipped/failed) · `completion_probability` ·
`is_flexible` · `order_index` · `standards[]`

### PlanRead
`id` · `user_id` · `version` · `status`(active/superseded/draft/completed/archived) · `title` ·
`start_date` · `end_date` · `parent_plan_id` · `confidence` · `created_at` ·
`tasks[]`(TaskRead) · `goals[]`(GoalRead，由该计划任务的 goal_id 反查)

### GoalDetailRead
`id` · `title` · `description` · `goal_type` · `status`(active/**draft**/completed/archived/cancelled) ·
`deadline` · `priority`(1–4) · `estimated_minutes` · `created_at`

### InsightRead
`plan_id` · `total_tasks` · `completed_tasks` · `completion_rate` · `total_planned_minutes` ·
`total_actual_minutes` · `avg_stress` · `avg_energy` · `high_cognitive_minutes` ·
`predicted_vs_actual_ratio` · `cognitive_load_breakdown` · `daily[]` · `recommendations[]` ·
(建议)`data_sufficiency` · (建议)`drivers[]`

### SituationTrendRead
`points[]`(`date`/`energy`/`stress`/`efficacy`) · `samples` · `min_samples` · `sufficient` · `drivers[]`

### PlanChangeRead
`id` · `trigger_type` · `reason` · `old_version` · `new_version` · `created_at` · `days[]`
(`date`/`added`/`moved`/`removed`/`summary`/`task_ids`)

---

## 11. 后端实现时序建议

1. **P0**：`POST /plans/decompose` + `POST /plans/confirm`，并接真智能体——目标页拆解才成立。
2. **P1**：`GET /users/me/preferences` + `PUT`，并让 generate 回退读；`GET /plans/{id}/changes`；
   `GET /users/me/situation/trends` + `InsightRead` 扩展。
3. **P2**：`/goals` CRUD（含 draft）——待拆解清单跨设备；更长周期计划（月视图）。
