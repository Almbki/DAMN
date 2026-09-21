# 前端重构 · 后端接口缺口清单

按新的界面 IA（待办 / 画像 / 目标 / 设置）整理。当前前端对缺口功能**用本地 mock 实现**，
后端补齐后只需替换 `frontend/src/api/endpoints.ts` 里的实现，UI 不用动。

图例：✅ 已有 · 🟡 可用但不够 · 🔴 完全没有（前端先 mock）

---

## 1. 计划变更提示（右上角"系统改了未来哪几天"）🔴

**现状**：`ReplanEvent`（`app/domain/models/replan_event.py:17-26`）只存
`changed_tasks: list[int]`（任务 id），**没有日期**；`ReplanEventRepository.list_by_plan`
(`replan_event_repository.py:29`) 存在但没有任何路由调用；只有 cooldown 用了
`get_latest_for_user`。所以"改了哪几天"前端算不出来。

**建议接口**（二选一）：

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
      { "date": "2026-09-22", "added": 2, "moved": 1, "removed": 0,
        "task_ids": [12, 13] }
    ]
  }]
```

或用户级：`GET /api/v1/users/me/replan-events`。

要点：服务端在 `ReplanService.replan` 里已经能拿到旧/新 `(scheduled_date, start_time,
end_time)`（`replan_service.py:136-141`），把 **date diff** 一起写进 `ReplanEvent` 即可。

---

## 2. 目标列表与进度（GOAL 页）🔴

**现状**：没有任何 goals 路由（`app/api/router.py:7-15` 只注册 auth/users/plans/feedback/
tasks/insights）；目标只在生成计划时被隐式创建（`plan_service.py:117-133`），只能从
`PlanRead.goals` 里读到当前版本的目标。`GoalStatus` 没有 `draft`
（`app/domain/models/enums.py:16-20`：active/completed/archived/cancelled）。

> 注：`AGENTS.md` 里"`PlanRead.goals` 映射错误"的说明与当前代码不符 ——
> `plan_service.py:234-235` 是用任务的 `goal_id` 反查，当前实现是对的。

**建议接口**：

```
GET  /api/v1/goals                → [{id,title,description,status,goal_type,deadline,
                                      priority,estimated_minutes,created_at,
                                      completed_minutes,total_minutes,progress}]
POST /api/v1/goals                body GoalCreate → GoalRead   # 支持 status=draft
PATCH /api/v1/goals/{id}          body GoalUpdate → GoalRead
DELETE /api/v1/goals/{id}         → 204
```

进度（时间加权）由服务端算好最好；前端兜底算法见 `frontend/src/domain/goal.ts`。

---

## 3. 批量拆解（GOAL：多条待拆解任务 → 每天的任务）🔴

**现状**：`POST /plans/generate` 是同步直接落库（`plans.py:73`，请求体
`PlanGenerateRequest`），没有"先出预览、可重新生成、可取消"的中间态。GOAL 页现在允许
用户先攒**多条待拆解任务**，再一次性交给系统拆解。

**建议接口**：

```
POST /api/v1/plans/decompose
body {
  "goals": [{ "title": str, "priority": int, "deadline": date|null, "notes": str }],
  "feedback": str|null        # 用户对上一版预览的意见，用于「重新生成」
}
→ {
  "draft_id": "uuid",
  "days": [
    { "date": "2026-09-22",
      "tasks": [{ "title": str, "priority": int, "estimated_minutes": int,
                  "start_time": "09:00:00", "end_time": "10:00:00" }] }
  ]
}

POST /api/v1/plans/confirm  body { "draft_id": "uuid" } → PlanRead     # 落库
```

- 「重新生成」= 同一个 `draft_id` 再调一次 `decompose`，带上新的 `feedback`。
- 取消 = 待拆解项留在前端本地；若想跨设备保留，走 §2 的 `POST /goals`（status=draft）。

**当前前端 degrad**：`frontend/src/domain/decompose.ts` 用本地启发式（按 notes 分行、
按优先级/截止分散到每天、给时段），「重新生成」用关键词规则（下午/少一点/周末/今天/明天）
重排；确认时把预览写进 `GoalCreate.description` 再调既有 `POST /plans/generate`，并在弹窗里
明写"拆解由后端智能体完成，当前为本地模拟预览"。

---

## 4. 拆解由后端智能体完成（反馈 → 重排的闭环）🔴

**现状**：无独立拆解/对话接口；且 `app/agent/nodes/*` 是确定性启发式、`MockLLMClient`
返回固定 JSON（见根 `AGENTS.md`），**不是真 LLM**。所以"理解多条大目标、拆成每天任务分配"
这件事目前后端做不到。

**建议**：把 §3 的 `POST /plans/decompose` 做成真正调智能体的入口（`feedback` 拼进 prompt，
在同一个 `draft_id` 上重复调用以支持「重新生成」）。核心拆解逻辑由后端接智能体完成。

**当前前端 degrad**：本地规则重排 + 弹窗写清"当前为本地模拟"。

---

## 5. 用户画像：趋势 / 数据是否够 / "为什么" 🔴（部分 🟡）

**已有**：`Feedback` 有 per-date `stress_level` / `energy_level`（`feedback.py:21-22`），
`GET /plans/{plan_id}/feedback` 可读当前计划的反馈；`InsightRead` 有 `avg_stress` /
`avg_energy` / `predicted_vs_actual_ratio` / `recommendations`。
`FeedbackRepository.list_by_user` 已实现（`feedback_repository.py:42-49`）但没有路由。

**缺**：
- 跨计划的趋势序列 → `GET /users/me/situation/trends?days=14`
  → `[{date, energy, stress, efficacy, sample}]`
- "数据够不够"阈值 → `InsightRead` 加 `data_sufficiency: {samples, min_samples, sufficient}`
- "系统为什么这么判断" → `InsightRead` 加 `situation_summary` / `drivers: [str]`
  （现有 `recommendations` 面向计划，不针对精力/压力/效能状态）

**"效能"定义**：后端**没有**任何 efficacy 字段（`self_efficacy` 只出现在设计文档里）。
当前前端用合成指标：`execution_weight` 为底，用近 14 天完成率校正（见
`frontend/src/domain/situation.ts`），并在"为什么"里写清算式。

---

## 6. 用户情况（user_situation）未暴露 🟡

`app/agent/nodes/user_situation_analysis.py` 产出的 `UserSituationResult`
（`agent/schemas.py:57-71`：`duration_factor`、`completion_ability`、`stress_state`、
`fatigue_state`、`recommended_time_slot`、`should_reduce_load`、`confidence`）
只活在 graph state 里，**不落库、无接口**。若画像要显示"系统判断"，最省事的是把最近一次
`UserSituationResult` 存到 plan 或 user_model，再随 `InsightRead` 一起返回。

---

## 7. 排程偏好持久化（设置页"设一次就一直生效"）🔴

**现状**：`available_minutes_per_day` / `daily_limit_minutes` / `buffer_minutes` /
`high_cognitive_max_per_day` 只从 `PlanGenerateRequest` 进（`plans.py:60-63`），
在 `rule_validation.py:76-80` 消费；`user.profile` 是自由 JSON
（`domain/models/user.py:20-24`），`generate` **从不读它**，也没有 typed 偏好表
（`user_model.py` 只有 ML 特征，无作息/可投入时间）。

**建议**（二选一）：

```
PATCH /api/v1/users/me  { "profile": { "scheduling_preferences": {
  available_minutes_per_day, daily_limit_minutes, buffer_minutes,
  high_cognitive_max_per_day, sleep_start, sleep_end } } }
```

并让 `_to_generation_request`（`plans.py:60`）在请求体缺省时**回退读用户偏好**。
或新增 typed：`GET/PUT /users/me/preferences`。

**前端 degrad**：偏好存本地（`localStorage` / 内存），compose 进每次
`PlanGenerateRequest` 的对应字段，因此"一次设置、每次自动带上"已经生效，
只是换设备不同步。

---

## 8. 待办视图

| 功能 | 状态 | 说明 |
| --- | --- | --- |
| 今日 | ✅ | `PlanRead.tasks[].scheduled_date` 够用 |
| 本周 | ✅ | 前端按周一~周日聚合，无需新接口 |
| 每月 | 🔴 | 默认 horizon 只到 `today+13`（`schemas/plan.py`），月视图没数据；按钮先置灰 |
| 全部/未完成筛选 | ✅ | 前端 |
| 按目标分组 | ✅ | `TaskRead.goal_id` 可信（`mapper.ts`） |
| 任务勾选完成 | ✅ | `PATCH /tasks/{id} {completed:true}`；取消用 `{status:'scheduled'}` |
| 每日反馈 | ✅ | `POST /plans/{id}/feedback` |
| 跳过 | ✅ | `PATCH {status:'skipped'}` |

---

## 9. 其它已知（沿用，不新增）

- 取消完成必须走 `status:'scheduled'`（`completed:false` 是 no-op，
  `api/mapper.ts:44`）。
- feedback `completion_rate < 0.5` 会自动生成新版本，前端要切到 `replan_plan_id`
  （新版本可能 0 任务）；重排冷却 24h，per-user，409 带 `next_eligible_at`。
- `PATCH /users/me` 的 `profile` 是全量覆盖语义（`auth_service.py:59-80` 只在非 None 时写），
  前端更新偏好时应合并后在本地维护，别依赖服务端 patch 合并。
