# 长期目标调度 P0 修复报告

> **这份文档记录什么**：本次 P0 事故的最终修复结果，包括根因、架构决策、
> schema/scheduler/prompt 改动、迁移结论、回归测试和实际命令结果。
> 第一阶段的完整数据流追踪和取证见同目录 `00-根因分析.md`。
>
> **怎么使用**：
> 1. 想快速了解「为什么 7 个第N天会挤在同一天」→ 读「一、根因」；
> 2. 想 review 设计是否合理 → 读「二、架构决策」「三、schema」；
> 3. 想验证修复 → 读「六、回归测试」和「七、实际测试结果」；
> 4. 想知道还没做什么 → 读「八、剩余限制」。
>
> **结论先行**：事故不是 scheduler 只排了 7 天，而是 LLM 的「每天」从未变成
> 机器可读的 recurrence；deterministic expansion 因条件不满足被静默跳过；
> 7 个没有日期约束的 one-off 被 scheduler 贪心塞进同一天。修复把 recurrence
> 语义显式化，把日期展开收敛到一个 deterministic、可校验、fail-closed 的模块。

---

## 一、根因

### R1（主因）重复语义没有进入 deterministic 层

- `GoalAnalysisResult` / `AnalyzedGoal` 原来只有 `objective / subtasks /
  constraints`，没有 `goal_kind` / `recurrence` / `work_units`。
- `plan_generation` 原来不接收 `goal_analysis`。
- 因此用户说的「每天」只能变成一条自然语言 constraint，无法驱动日期展开。

### R2 展开触发条件过窄且会静默跳过

旧的 `_expand_recurring_goals` 只在 LLM 路径调用，并依赖：

1. 合法 1-based `goal_id`；
2. `_infer_task_kind(goal)` 不是 `ONE_OFF`；
3. group 里不能已有 `occurrence_date`。

任意一条不满足就原样返回，没有错误、没有 warning、没有 fail-closed。

### R3 `long_term` 被错误等同于「每日重复」

旧的 `_infer_task_kind` 把 `GoalType.LONG_TERM` 和 `GoalType.PROJECT` 都映射成
`TaskKind.LONG_TERM`，后续按天复制。课程/项目型目标因此会被错误地日复一日复制。

### R4 prompt 诱导按日期枚举

`initial_plan.md` 的「Split work into checkable units」没有区分「一个 occurrence
内部的 checkable steps」和「按日期枚举 occurrence」；叠加默认 13 天 horizon，
模型自然输出「第1天…第7天」。

### R5 缺少 fail-closed 的 series 校验

旧规则只保证 `scheduled_date >= occurrence_date`（earliest）和
`scheduled_date <= deadline`（deadline），没有检查：

- 同一 series 同一 occurrence_date 重复；
- `scheduled_date` 是否等于 `occurrence_date`；
- 声明的 recurrence 生命周期是否完整物化；
- occurrence 是否落在 goal 的 `[start, end]` 内。

同时 `_persist_final_plan` 会静默丢弃没有排上槽位的 recurring occurrence。

### R6 scheduler horizon/起点依赖 today

`default_horizon` 的起点永远是 today，终点只被 task deadline 撑大；plan 的
`end_date` 直接复制 `request.end_date`（默认 today + 13）。因此长期 goal 的
2027-07-01 不会进入 plan 元数据，scheduler 也不会显式知道 plan/goal 生命周期。

### 为什么「第1～7天」全部在同一天

1. LLM 输出 7 个 title 为「第1天…第7天」的 draft；
2. 这些 draft 没有 `occurrence_date` / `deadline`；
3. 展开条件未满足，保持 `ONE_OFF`；
4. scheduler 从 today 开始贪心放置，7×20=140 分钟 < 300 分钟日容量；
5. 全部落在 10-26。**「第N天」只是 UI 文本，scheduler 从未读取它。**

### 为什么只有一周

- 后端常量是 13 天（不是 7 天）；7 是 LLM 自己枚举的条数。
- 展开没有运行，所以没有 deterministic 的 249 天 occurrence。
- 前端「本周」只渲染当前自然周，月视图是占位，进一步放大了观感。

---

## 二、架构决策

采用 **goal 行即 recurrence template + eager full-range deterministic
materialization**：

```
Goal (start_date, deadline, task_kind, recurrence_weekdays, daily_target_minutes)
  + GoalAnalysisResult (goal_kind, recurrence, work_units)   <- LLM 语义
        |
        v
Deterministic resolver (explicit metadata > LLM classification > legacy goal_type)
        |
        +-- ONE_OFF  -> 1 个普通 draft
        +-- RECURRING -> RecurrenceRule -> deterministic occurrence expansion
        |                  -> series drafts (occurrence_date, series_id, index)
        +-- PROJECT  -> 有限 work_unit 序列（不按天复制）
        |
        v
Scheduler (occurrence_date = earliest, occurrence_date = deadline)
        |
        v
RuleEngine (series duplicate / wrong-day / completeness)
        |
        v
Persist (occurrence rows; 不再静默丢弃)
```

### 为什么选择 eager，而不是 rolling

- 与现有 `tasks.series_id / occurrence_date` 数据模型和既有测试完全兼容；
- 不需要新增 recurring job / materializer / 后台任务基础设施；
- 249 条 / goal 对 SQLite/Postgres 都可接受；
- `occurrence_date == deadline` 约束能保证「每天恰好一条」。

**明确代价**：每个 plan version 会复制整段 occurrence；replan 会新增 N 行；
超长 goal 需要上限。本次设置 `MAX_OCCURRENCES_PER_SERIES = 2000`，超过则
`RecurrenceError` **明确失败**，不静默截断。

### 责任边界

- **LLM**：只判断 `goal_kind`、recurrence 频率、project 的有限 work units；
  不计算天数、不枚举日期、不输出「第N天」。
- **Deterministic**：日期运算、inclusive 边界、occurrence 展开、series id、
  order_index、scheduler 约束、容量、落库、校验。
- **禁止**：regex 解析「每天/每周」；根据 title「第N天」猜日期；
  复制最后一个 draft 填日期。

### 边界语义

- `start_date`、`end_date` 均 **inclusive**。
- DAILY：`start, start+interval, ... <= end`。
- WEEKLY：`start..end` 内选择 `weekdays`；`interval` 以 start 所在周为锚点。
- `weekdays` 为空 + weekly → 使用 `start_date.weekday()`。
- 同一天同一 series 恰好一个 occurrence。
- 空 occurrence / 非法范围 / 超过 2000 条 → `RecurrenceError`。

---

## 三、Schema 改动

### Agent schema（不落库）

| 文件 | 改动 |
|---|---|
| `app/agent/schemas.py` | 新增 `GoalKind`（one_off/recurring/project）、`RecurrenceSpec`（frequency/interval/weekdays）、`WorkUnit`；扩展 `AnalyzedGoal`；`PlanGenerationResult.series_specs` |
| `app/domain/recurrence.py` | 新增 `RecurrenceRule`、`RecurrenceError`、`RecurrenceFrequency`、`SeriesSpec`、`MAX_OCCURRENCES_PER_SERIES` |
| `app/domain/scheduling/schedule_result.py` | `ScheduledTask` 增加 `series_id` / `occurrence_date`（从 Task 复制，供规则校验） |

### 数据库 / 公开 API

- **没有新增数据库列/表**。
- `goals` / `tasks` 的 recurrence/series 列已由既有迁移
  `alembic/versions/d0853f9e14b4_task_kinds_and_occurrence_series.py` 创建。
- `TaskRead` / `PreviewTaskRead` 原本就包含 `task_kind / series_id /
  series_index / occurrence_date`，公开 API 契约未变。

### 关键实现

- `app/agent/tools/task_decomposer.py`：
  - deterministic fallback 只依据显式 `task_kind / goal_type /
    recurrence_weekdays` 分类，**不解析文本**；
  - LLM 结果做互斥归一化（recurring 不带 work_units，project 不带 recurrence）。
- `app/agent/tools/plan_drafter.py`：
  - 统一 `_materialize`，LLM 路径和 fallback 路径共用同一套日期逻辑；
  - `_resolve_goal_kind`：显式 ROUTINE/ONE_OFF > LLM classification >
    legacy goal_type；`LONG_TERM` 歧义交给 analysis；
  - `_materialize_recurring`：`RecurrenceRule.occurrences()` 一日期一 draft；
  - `_materialize_project`：有限 work units，`MAX_PROJECT_WORK_UNITS = 60`；
  - `_materialize_one_off`：保持 one-off，清理 series/occurrence；
  - 忽略 LLM 输出的近似日期字段，recurring/project 的日期全部由代码决定。
- `app/agent/nodes/plan_generation.py`：把 `goal_analysis` 传给 drafter；
  `RecurrenceError` 直接 re-raise（fail closed）。
- `app/agent/nodes/_shared.py`：
  - RuleContext 增加 `schedule_start/end`、`series_specs`、`series_occurrences`；
  - goal 的 start_date 也作为 non-occurrence task 的最早日期。

---

## 四、Scheduler 改动

`app/domain/scheduling/scheduler.py`：

1. `default_horizon` 优先使用显式 `context.schedule_start` / `schedule_end`，
   不再只依赖 `today + 13`；仍被 task deadline 撑大。
2. `_first_feasible` 对 materialized occurrence 做 deadline clipping：
   occurrence 的 `deadline` 就是 `occurrence_date`，当天容量不足时**保持
   unscheduled**，绝不漂移到后一天。one-off 保持旧 candidate 行为（由
   deadline 规则 + repair 处理）。
3. `ScheduledTask` 复制 `series_id` / `occurrence_date`，供
   `RecurrenceConsistencyRule` 校验。

`app/domain/scheduling/schedule_result.py` + `scheduler.py` 的配合保证：
「occurrence 只能落在 occurrence_date，容量不足则 PENDING，不移动。」

`app/application/services/plan_service.py`：

- 不再过滤掉没有槽位的 recurring occurrence；
- 有槽位 → `SCHEDULED`，无槽位 → `PENDING`（`scheduled_date=None`）；
- plan 的 `start_date/end_date` 由 `finalization` 按 goal/occurrence 生命周期计算，
  不再只是 `request.end_date`（today+13）。

`app/agent/nodes/repair.py`：

- `_pick_drop` 不再丢弃带 `series_id` 的 draft（recurring occurrence 和 project
  work unit 都受保护）；无法排上时保留为 PENDING，避免静默截断。

`app/domain/rules/recurrence_consistency.py`（新规则，已注册到
`default_rules()`）：

- `recurrence_duplicate`：同 series 同 occurrence_date 重复；
- `recurrence_wrong_day`：scheduled_date != occurrence_date；
- `recurrence_out_of_range`：occurrence 超出 `[start_date, end_date]`；
- `recurrence_incomplete`：materialized set 少于规则期望（展开被截断）；
- `recurrence_unexpected`：出现规则之外的 occurrence；
- `recurrence_invalid`：规则本身无法展开。

---

## 五、Prompt 改动

四个 prompt 已改为「LLM 只输出机器可读语义，不负责日期调度」：

1. `app/agent/prompts/goal_analysis.md`
   - 要求输出 `goal_kind`（one_off/recurring/project）、`recurrence`
     （frequency/interval/weekdays）、`work_units`（project，5-30 个）；
   - 明确 recurring 不枚举 occurrence/日期/「Day 1..N」，不计算天数；
   - project 输出有限 topic 序列，不每天重复同一任务；
   - one_off 是单一交付物。

2. `app/agent/prompts/initial_plan.md`
   - 把「Split work into checkable units」限定为「一个 occurrence/work unit
     内部的 `standards`」，绝不跨日期；
   - recurring：每个 goal 只输出一个 reusable template，不输出每天一条；
   - project：输出有限、有序的 work-unit drafts；
   - 新增 `GOAL ANALYSIS` 变量块。

3. `app/agent/prompts/replanning.md`
   - recurring：保留 template，只输出一次；不重新枚举日期；不把 series 变 one-off；
   - project：保留有限 work units，不每天重复。

4. `app/agent/prompts/adjustment.md`
   - 保留每个 occurrence 的 `series_id` / `occurrence_date`；
   - 不合并不改日期、不把 series 变 one-off。

---

## 六、Migration

**不需要 migration。**

- `goals.start_date / task_kind / daily_target_minutes / recurrence_weekdays /
  target_*` 与 `tasks.task_kind / series_id / series_index / occurrence_date /
  target_*` 已由 `d0853f9e14b4_task_kinds_and_occurrence_series.py` 创建。
- 本次新增的 `GoalKind / RecurrenceSpec / WorkUnit / SeriesSpec` 只存在于
  Agent state / checkpoint，不落库。
- `ScheduledTask.series_id / occurrence_date` 是内存值对象字段，不落库。
- 未来若切换 rolling materialization，才需要新增 template 表/列；本次明确不做。

---

## 七、回归测试

新增 **27** 个测试：

### `tests/unit/test_recurrence.py`（13 个）
纯 deterministic expansion：
- 跨月 daily inclusive（2026-10-26 → 2026-11-05，11 天）；
- 长跨度（2026-10-26 → 2027-07-01，249 天）；
- 每周六 / 双周六；
- weekly 默认 start weekday；
- start == end；
- 非法范围 / 非法 interval / 非法 weekday / 非法 frequency；
- weekly 范围内无匹配 weekday；
- 2000 条上限；
- `contains()`。

### `tests/unit/test_recurrence_materialization.py`（13 个）
覆盖用户要求的 8 类场景：
1. **跨月 daily**：11 个 occurrence，每个自然日一条，scheduler 不会全塞 10-26；
2. **长跨度**：249 个 occurrence，首日 2026-10-26，末日 2027-07-01；
   LLM classification 在 `task_kind` 缺失时也能驱动；
3. **one-off**：「10月30日前完成实验报告」→ 1 个 draft，无 series/occurrence；
4. **finite project**：「学完高等数学」→ 有限 work units（极限/导数/…），
   不是 249 个 day copy，`task_kind=ONE_OFF`，无 occurrence_date；
5. **weekly**：每周六，所有 occurrence `weekday()==5`；
6. **capacity**：daily recurring + 90 分钟 one-off，daily_limit=120；
   `daily_minutes <= 120`，occurrence 不移动，容量不足则 unscheduled；
7. **boundary/fail-closed**：start==end → 1 条；倒序范围 → `RecurrenceError`；
8. **series rule**：duplicate / wrong-day / incomplete / complete。

### `tests/agent/test_long_term_horizon.py`（1 个）
- 30 天 daily goal：preview 30 条、confirm 后持久化 30 条、plan.end_date 覆盖
  真实 end_date、`GET /plans/{id}` 返回 30 条，第 8 天以后存在 23 条任务。
- 证明「7 天」是 view horizon，不是 API/recurrence 生命周期截断。

### 既有测试调整
- `tests/unit/test_task_kinds.py`：倒序范围从「静默回退 one-off」改为
  **fail-closed `RecurrenceError`**（符合用户要求的 §9）。
- `tests/api/test_profile_api.py`：legacy 投影与嵌套值改为 `pytest.approx`
  （原断言是 `0.5 == 0.49999999999999994` 的浮点精度问题，与本次改动无关）。

---

## 八、实际测试结果

以下命令均在本机实际执行（Windows / PowerShell / Python 3.12 / uv）：

| 命令 | 结果 |
|---|---|
| `uv run pytest --tb=short --disable-warnings -q` | **全量 267 个用例，最终运行 100% 通过（无 F）** |
| `uv run pytest tests/unit/test_recurrence.py tests/unit/test_recurrence_materialization.py tests/agent/test_long_term_horizon.py -q` | **27 个新增 recurrence 测试全部通过** |
| `uv run pytest tests/unit/test_task_kinds.py tests/unit/test_scheduler.py tests/unit/test_rules.py tests/agent/test_preview_flow.py tests/agent/test_repair.py -q` | **全部通过** |
| `uv run ruff check .` | **All checks passed** |
| `uv run pytest --collect-only -q` | **collected = 267** |

补充说明（如实记录中间过程）：

- 第一次 `uv run pytest -q` 暴露 `tests/api/test_profile_api.py::
  test_feedback_refreshes_the_level2_state` 的浮点断言失败
  （`0.5 == 0.49999999999999994`）。这是 legacy 字段（round 6 位）与嵌套原值
  的精确浮点比较问题，与本次功能改动无关；已把该断言改为 `pytest.approx`
  （abs=1e-6），随后通过。
- 一次中间的全量复跑出现过 `tests/agent/test_feedback_routes.py::
  test_feedback_no_pressure_is_recorded_without_a_replan` 的顺序相关抖动；
  该测试单独运行、整个文件运行、以及最终全量运行均通过，确认与本次改动无关，
  但作为剩余风险记录。
- **未运行 frontend**：公开 API schema 未变化（`TaskRead` / `PreviewTaskRead`
  原本已有 series 字段），因此不满足「API/schema 变化才跑 frontend」的条件。
  前端长周期视图限制见下一节。

---

## 九、剩余限制

1. **Eager materialization 的规模代价**：249 条 / goal 会写入数据库；replan 会
   按版本复制整段 occurrence。`MAX_OCCURRENCES_PER_SERIES = 2000` 是硬上限，
   超过会明确失败。未来可切换 rolling horizon（只需要替换 materialization
   window，不改 schema/规则）。
2. **前端只显示今天 + 当前自然周**：`new_frontend/src/app/index.tsx` 的「本周」
   只渲染周一～周日，月视图是占位（约 14 天）。本次保证后端/API 数据完整，
   但更长周期的 UI 入口仍未实现。这是 view horizon，不是数据截断。
3. **过去日期的 occurrence**：如果 goal `start_date` 早于 today，过去的
   occurrence 会保留为 `PENDING`（无槽位），不会自动标记 skipped/missed；
   本次没有引入 rollover 语义。
4. **LLM 分类质量**：`goal_analysis` 的分类决定 recurring/project/one-off。
   如果真实模型把「每天」误判为 one-off，deterministic fallback 不会用 regex
   去纠正（这是有意的边界）。显式 `task_kind` 仍然优先。
5. **Series 编辑**：仍然按单条 task 编辑/删除；没有 series 级别的批量操作。
6. **测试抖动**：`test_feedback_routes` 存在一次顺序相关抖动；最终全量与单文件
   均通过，但值得后续排查共享状态。
7. **LangGraph checkpoint 警告**：新增的 `GoalKind` 类型在 checkpoint
   deserialization 时会打印 "unregistered type" 警告（非致命）。这是既有
   msgpack 白名单机制的问题，本次未改。
8. **没有迁移**：本次不新增数据库结构；如果未来要做 rolling/template 表，
   需要单独 migration。

---

## 十、改动文件清单

### 新增
- `app/domain/recurrence.py`
- `app/domain/rules/recurrence_consistency.py`
- `tests/unit/test_recurrence.py`
- `tests/unit/test_recurrence_materialization.py`
- `tests/agent/test_long_term_horizon.py`
- `修复/00-根因分析.md`
- `修复/LONG_TERM_SCHEDULING_FIX_REPORT.md`

### 修改
- `app/agent/schemas.py`
- `app/agent/tools/task_decomposer.py`
- `app/agent/tools/plan_drafter.py`
- `app/agent/nodes/plan_generation.py`
- `app/agent/nodes/_shared.py`
- `app/agent/nodes/finalization.py`
- `app/agent/nodes/repair.py`
- `app/agent/prompts/goal_analysis.md`
- `app/agent/prompts/initial_plan.md`
- `app/agent/prompts/replanning.md`
- `app/agent/prompts/adjustment.md`
- `app/domain/rules/base.py`
- `app/domain/scheduling/schedule_result.py`
- `app/domain/scheduling/scheduler.py`
- `app/application/services/plan_service.py`
- `tests/unit/test_task_kinds.py`
- `tests/api/test_profile_api.py`（仅浮点断言修正）

> 注：工作区在本次会话开始前已存在其他未提交修改（例如
> `app/agent/context.py`、`app/agent/nodes/preview.py`、
> `app/application/services/user_model_service.py`、前端
> `course-timetable.tsx` 等）。本报告只列出本次 P0 修复实际改动的文件；
> 全量测试是在包含这些既有改动的联合工作区上执行的。

---

## 十一、手工验证建议

1. 启动 API：`uv run uvicorn app.main:app --reload` → http://localhost:8000/docs
2. 用 `POST /api/v1/plans/preview` 提交：
   ```json
   {
     "goals": [{
       "title": "每天背考研英语单词",
       "goal_type": "habit",
       "task_kind": "routine",
       "start_date": "2026-10-26",
       "deadline": "2027-07-01",
       "daily_target_minutes": 20
     }],
     "start_date": "2026-10-26",
     "end_date": "2027-07-01"
   }
   ```
3. 预期：preview 返回 249 个任务，`series_id = "goal-1-routine"`，
   `occurrence_date` 从 2026-10-26 到 2027-07-01 每天一条，
   `scheduled_date == occurrence_date`。
4. confirm 后 `GET /api/v1/plans/{id}` 仍返回 249 条，`plan.end_date` 为
   `2027-07-01`（不是 today+13）。
5. 如果临时把 `deadline` 改成早于 `start_date`，系统应明确失败（`RecurrenceError`），
   而不是静默生成错误计划。

---

## 十二、一句话总结

**修复的核心不是「让 LLM 多输出日期」，而是把「每天」变成
`GoalAnalysisResult.recurrence` → `RecurrenceRule` → deterministic
occurrence instances；scheduler 只知道实例和真实日期，rule engine 负责
fail-closed 校验。**
