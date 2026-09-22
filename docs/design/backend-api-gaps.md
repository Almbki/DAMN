# 前端 · 后端接口需求清单

按界面 IA（**待办 / 画像 / 目标 / 设置**）整理。前端对缺口功能先用**本地 mock / 本地规则**兜底，
后端补齐后只改 `frontend/src/api/endpoints.ts` 与对应 provider，UI 不用动。

图例：✅ 已有 · 🟡 可用但不够 · 🔴 完全没有（前端先 mock）

## 总览

| 优先级 | 接口 | 用在哪 | 现状 |
| --- | --- | --- | --- |
| **P0** | `POST /plans/decompose` + `POST /plans/confirm` | 目标页「拆解」预览 / 确认 | 🔴 |
| **P0** | 真智能体接进拆解（替换 `MockLLMClient`） | 目标页拆解质量 | 🔴 |
| **P1** | `GET /plans/{id}/changes`（或 `/users/me/replan-events`） | 待办右上「计划变更」 | 🔴 |
| **P1** | `GET /users/me/situation/trends` + `InsightRead` 扩展 | 画像（趋势 / 数据够不够 / 为什么） | 🔴 |
| **P1** | 排程偏好持久化（`PATCH /users/me` 且 `generate` 回读） | 设置 | 🔴 |
| **P2** | `GET/POST/PATCH/DELETE /goals`（含 `draft`） | 待拆解项跨设备保留 | 🔴 |
| **P2** | 更长周期计划（月视图） | 待办「每月」 | 🔴 |
| ✅ | 任务字段 `priority` / `start_time` / `end_time` | 待办时间轴 | 已有，前端已开始读取 |

---

## 1. 批量拆解（目标页：多条待拆解任务 → 每天的任务）🔴 **P0**

**前端现状**：目标页允许先攒**多条待拆解任务**（标题 / 优先级 / 截止 / 补充），点「拆解」后
一次性预览，可「重新生成」或「就先这样」。`POST /plans/generate`（`app/api/v1/plans.py:73`）
是一步到位落库，没有"先出预览、可重新生成、可取消"的中间态。

**建议接口**：

```
POST /api/v1/plans/decompose
body {
  "goals": [
    { "title": str, "priority": int, "deadline": "YYYY-MM-DD" | null, "notes": str }
  ],
  "feedback": str | null        # 用户对上一版预览的意见，「重新生成」时带上
}
→ 200 {
  "draft_id": "uuid",
  "days": [
    { "date": "2026-09-22",
      "tasks": [
        { "title": str, "priority": int, "estimated_minutes": int,
          "start_time": "09:00:00", "end_time": "10:00:00",
          "source_index": 0 }   # 这条来自 goals[0]，可选
      ] }
  ]
}

POST /api/v1/plans/confirm      body { "draft_id": "uuid" } → 200 PlanRead
```

- 「重新生成」= 用**同一个 `draft_id`** 再调一次 `decompose`，带新的 `feedback`。
- 「就先这样」= `confirm` 落库，返回 `PlanRead`（前端直接 `applyPlan`）。
- 取消 = 待拆解项留在前端本地；要跨设备保留见 §2。

**前端兜底**：`frontend/src/domain/decompose.ts` 本地启发式（按 notes 分行、按优先级/截止
分散到每天、给时段）；「重新生成」用关键词规则（下午 / 少一点 / 周末 / 今天 / 明天）重排；
确认时把预览写进 `GoalCreate.description` 再调既有 `POST /plans/generate`。弹窗已写明
"拆解由后端智能体完成，当前为本地模拟"。

---

## 2. 目标 / 待拆解草稿的持久化 🟡 **P2**

**前端现状**：目标页**不再有目标列表/进度条**；`PlanRead.goals` 只用来给待办「按目标分组」
当标题（`plan_service.py:234-235` 用任务 `goal_id` 反查，当前实现是对的）。

**真正缺的**：待拆解清单和草稿目前只在前端内存里，刷新即丢。若要跨设备/刷新保留：

```
POST /api/v1/goals                body GoalCreate → GoalRead   # status 支持 "draft"
GET  /api/v1/goals?status=draft   → [{id,title,notes,priority,deadline,status}]
PATCH /api/v1/goals/{id}          body GoalUpdate → GoalRead
DELETE /api/v1/goals/{id}         → 204
```

> 注：`GoalStatus`（`app/domain/models/enums.py:16-20`）目前只有
> active/completed/archived/cancelled，**没有 draft**。
> `AGENTS.md` 里"`PlanRead.goals` 映射错误"的说明与当前代码不符，可忽略。

---

## 3. 计划变更提示（待办右上「系统改了未来哪几天」）🔴 **P1**

**为什么会有变更**：后端有自动重排——反馈 `completion_rate < 0.5` 且不在冷却内时，
`ReplanService.replan`（`app/application/services/replan_service.py`）会把未完成任务**重新排期**，
旧计划标 `superseded`、生成新版本。用户没主动改，所以需要把"改了哪几天、改了什么、为什么"讲清楚。

**现状**：`ReplanEvent`（`app/domain/models/replan_event.py:17-26`）只存
`changed_tasks: list[int]`（任务 id），**没有日期**；`ReplanEventRepository.list_by_plan`
存在但没有任何路由调用。所以前端算不出"改了哪几天"。

**建议接口**：

```
GET /api/v1/plans/{plan_id}/changes
→ 200 [{
    "id": 3,
    "trigger_type": "feedback_triggered",
    "reason": "auto replan: low daily completion rate",
    "old_version": 1,
    "new_version": 2,
    "created_at": "2026-09-21T09:00:00Z",
    "days": [
      { "date": "2026-09-22", "added": 2, "moved": 1, "removed": 0, "task_ids": [12, 13] }
    ]
  }]
```
或用户级 `GET /api/v1/users/me/replan-events`。

**要点**：`replan_service.py:136-141` 已经能拿到旧/新 `(scheduled_date, start_time, end_time)`，
把 **date diff** 一起写进 `ReplanEvent` 即可。

---

## 4. 拆解由后端智能体完成（反馈 → 重排闭环）🔴 **P0**

**现状**：`app/agent/nodes/*` 是确定性启发式、`MockLLMClient` 返回固定 JSON（见根 `AGENTS.md`），
**不是真 LLM**。所以"理解多条大目标、拆成每天任务分配"目前后端做不到。

**建议**：把 §1 的 `POST /plans/decompose` 做成真正调智能体的入口——`feedback` 拼进 prompt，
同一个 `draft_id` 上可重复调用以支持「重新生成」。核心拆解逻辑由后端接智能体完成。

---

## 5. 排程偏好持久化（设置页「设一次就一直生效」）🔴 **P1**

**现状**：`available_minutes_per_day` / `daily_limit_minutes` / `buffer_minutes` /
`high_cognitive_max_per_day` 只从 `PlanGenerateRequest` 进（`app/api/v1/plans.py:60-63`），
在 `rule_validation.py:76-80` 消费；`user.profile` 是自由 JSON
（`app/domain/models/user.py:20-24`），`generate` **从不读它**；也没有 typed 偏好表。

**建议**（二选一）：把偏好存进用户，并让 `_to_generation_request` 在请求体缺省时**回退读用户偏好**。

```
PATCH /api/v1/users/me  { "profile": { "scheduling_preferences": {
  "available_minutes_per_day": int, "daily_limit_minutes": int,
  "buffer_minutes": int, "high_cognitive_max_per_day": int,
  "sleep_start": "HH:MM", "sleep_end": "HH:MM" } } }
```
或新增 typed：`GET/PUT /api/v1/users/me/preferences`。

**前端兜底**：偏好存本地（`localStorage`），compose 进每次 `PlanGenerateRequest`，
"一次设置、每次自动带上"已生效，只是换设备不同步。

---

## 6. 画像：趋势 / 数据是否够 / "为什么" 🔴（部分 🟡）**P1**

**已有**：`Feedback` 有 per-date `stress_level` / `energy_level`（`app/domain/models/feedback.py:21-22`），
`GET /plans/{id}/feedback` 可读当前计划的反馈；`InsightRead` 有 `avg_stress` / `avg_energy` /
`predicted_vs_actual_ratio` / `recommendations`；`FeedbackRepository.list_by_user` 已实现但没路由。

**缺**：
- 跨计划趋势 → `GET /api/v1/users/me/situation/trends?days=14`
  → `[{ "date": "09-22", "energy": 6, "stress": 5, "efficacy": 0.62 }]`
- 「数据够不够」→ `InsightRead` 加 `data_sufficiency: { samples, min_samples, sufficient }`
- 「系统为什么这么判断」→ `InsightRead` 加 `situation_summary` / `drivers: [str]`

**"效能"定义**：后端没有任何 efficacy 字段（`self_efficacy` 只出现在设计文档里）。
前端现用合成指标 `0.6 × execution_weight + 0.4 × 近 14 天完成率`
（`frontend/src/domain/situation.ts`），并在"为什么"里写清算式。

---

## 7. 用户情况（user_situation）未暴露 🟡 **P2**

`app/agent/nodes/user_situation_analysis.py` 产出的 `UserSituationResult`
（`app/agent/schemas.py:57-71`：`duration_factor`、`completion_ability`、`stress_state`、
`fatigue_state`、`recommended_time_slot`、`should_reduce_load`、`confidence`）
只活在 graph state 里，**不落库、无接口**。若画像要显示"系统判断"，最省事是把最近一次
`UserSituationResult` 存到 plan 或 user_model，随 `InsightRead` 一起返回。

---

## 8. 待办页 / 时间轴

时间轴需要任务的**开始时间、结束时间、优先级**；这些 `TaskRead` **本来就有**
（`start_time` / `end_time` / `priority`），前端已开始读取（`api/mapper.ts`）。无需新接口。

| 功能 | 状态 | 说明 |
| --- | --- | --- |
| 今日（时间轴） | ✅ | `scheduled_date` + `start_time` + `end_time` + `priority` |
| 逾期分组 | ✅ | 前端按 `scheduled_date < today` 聚合 |
| 本周 | ✅ | 前端按周一~周日聚合 |
| 每月 | 🔴 | 默认 horizon 只到 `today+13`（`app/schemas/plan.py`），没数据；当前点了给提示 |
| 全部/未完成筛选 | ✅ | 前端 |
| 按目标分组 | ✅ | `TaskRead.goal_id` 可信 |
| 勾选完成 | ✅ | `PATCH /plans/{id}/tasks/{task_id} {completed:true}`；取消用 `{status:'scheduled'}` |
| 跳过 | ✅ | `PATCH {status:'skipped'}` |
| 每日反馈 | ✅ | `POST /plans/{id}/feedback` |

> 提醒：`TaskRead.priority` 要给出**有意义的档位**（前端按 `>=3 高 / 2 中 / 其它 低` 显示旗标）。
> 若当前生成的任务 priority 恒为同一个值，时间轴上会全一样。

---

## 9. 其它已知（沿用，不新增）

- 取消完成必须走 `status:'scheduled'`（`{completed:false}` 是 no-op，`frontend/src/api/mapper.ts`）。
- feedback `completion_rate < 0.5` 会自动生成新版本，前端切到 `replan_plan_id`（新版本可能 0 任务）；
  重排冷却 24h、per-user，409 带 `next_eligible_at`。
- `PATCH /users/me` 的 `profile` 是全量覆盖语义（`auth_service.py:59-80` 只在非 None 时写），
  前端更新偏好时本地合并后再整体提交，别依赖服务端 patch 合并。
- `/health` 在根路径（不在 `/api/v1`）；`POST /plans/generate` 是**同步**返回，别做 SSE 假进度。
