# PLANNING_PROMPT_SPEC v2

> **这是什么**：AI 自适应规划器的产品/契约规范。它定义 LLM 节点应该
> 如何理解目标、何时允许拆解、何时必须追问、work unit 的粒度、重复语义、
> 推进语义，以及 LLM 与 deterministic code 的权限边界。
>
> **这不是**：P0 事故复盘，也不是某一份 prompt 的逐字稿。六份 prompt 应在
> 本 spec 稳定后分别重写。
>
> **v2 修订重点**：把 v1 中「为防止 recurrence 事故而写的工程防守」升级为
> 「产品上应该如何规划」；同时修正了 v1 与当前产品方向不一致的 4 个点。

---

## 0. 本次修订：v1 中需要修正的地方

1. **`PROJECT + recurrence` 不是 LLM 的第四个 `goal_kind`。**
   - LLM 只输出 `goal_kind = one_off | recurring | project`。
   - `project_recurring` 是产品/API/DB/UI 的第四种 `PlanningMode`。
   - Prompt 中 `PROJECT + recurrence` 必须编码为：
     `goal_kind="project"` + `recurrence != null` + `work_units != []`。
   - 让模型输出 `goal_kind="project_recurring"` 会 schema 校验失败。

2. **RECURRING 是 opaque execution block，不是可拆解任务。**
   - Planner 默认不管理「新词多少、复习多少、遗忘曲线、错词」。
   - 这些属于外部 domain app（背单词软件、Keep、Anki）。
   - 默认 `subtasks = []`、`work_units = []`、`standards = []`。
   - 除非用户明确要求 Planner 管理内部步骤，否则不要编造 checklist。

3. **Work unit 没有「至少 5 个」这种数量下限。**
   - 数量由语义决定；典型 2–12 个；复杂项目可以更多。
   - 硬上限 60。
   - **禁止为了凑数量制造无意义 work unit。**
   - 判断粒度用语义标准，不用数量标准（见 §6）。

4. **信息不足时必须追问，不能用 goal title 糊一个 work unit。**
   - 新增 `decomposition_status = ready | needs_clarification` 和
     `missing_information[]`。
   - 例如「30 天学高数」但不知道当前进度/范围/教材 → `needs_clarification`。
   - 图应在 `goal_analysis` 后分流；`needs_clarification` 不进入
     `theoretical_analysis`。
   - v1 的「project 没有 work units → 用 goal 标题作为最小 unit」是错的，
     已从规划器 fallback 中移除。

5. **Theoretical workload 应该是 work-unit-level。**
   - 不是「学高数 = 480min」，而是「中值定理 = 120min，导数应用 = 180min…」。
   - `TheoreticalItem` 已增加 `goal_id` 和 `work_unit_index`。
   - Recurring 只估计**单次 occurrence**，不估计 249 天总工作量。

6. **`PROJECT_RECURRING` 的「一天一个 work unit」是 v1 简化，不是永久契约。**
   - 当前实现：第 i 个 work unit ↔ 第 i 个 occurrence。
   - 未来契约：`Work Unit → Execution Chunk → Occurrence`。
   - 例如「中值定理 120min」+「每天 30min」→ 4 个 execution chunks。
   - 本文档不把 1:1 写成永恒原则；实现状态见 §17。

7. **Level 1 / Level 2 不只有禁止项，还要有正面权限表。**
   - Level 1 影响长期策略；Level 2 影响当前执行负荷。
   - 两者都不能改变 goal 内容、curriculum、deadline、recurrence。
   - 详见 §13.2。

8. **原 v1 的「project 没有 work units → 用 drafts/goal 标题」已被移除。**
   - 现在的 deterministic fallback 是：`needs_clarification` 或 fail closed。
   - 不允许用「学高数」一个假 unit 掩盖信息缺失。

---

## 1. 规划器角色

你是确定性自适应规划系统中的一个 **推理组件**，不是日历。

- 你不直接安排日期、开始/结束时刻。
- 你把自然语言目标转化为 **结构化、机器可读的规划决策**：
  - 目标是什么；
  - 是否属于 one_off / recurring / project；
  - 是否有足够信息可靠拆解；
  - 重复节奏是什么；
  - 有意义的内容/阶段如何推进；
  - 理论工作量大概多少；
  - 基于证据如何解释。
- 你的输出是 **candidate**。deterministic 层负责实例化、调度、校验、持久化。

**一句话**：
> LLM 决定「做什么、属于哪类、内容怎么推进、信息够不够」；
> deterministic code 决定「哪一天、几点、能不能排下、是否合法」。

---

## 2. 权限层级

从高到低：

1. **系统硬不变量 / RuleEngine**
   - 容量、deadline、earliest start、固定事件、series 一致性。
   - 任何 LLM 输出、偏好、repair 都不能绕过最终硬校验。
2. **用户显式结构化数据**
   - `planning_mode`、`start_date`、`deadline`、`recurrence_*`、
     `daily_target_minutes`、`estimated_minutes`、`target_*`。
   - 显式数据优先于 LLM 推断；非法数据 fail closed。
3. **确定性推导 / 默认值**
   - 例如 legacy `task_kind=LONG_TERM` 无 analysis → recurring；
     weekdays 空/7 天 → daily；缺 deadline → request horizon。
4. **LLM 语义提案**
   - `goal_kind`、`recurrence`、`work_units`、`subtasks`、`objective`、
     `constraints`、理论工作量、narrative。
   - 只能是 candidate；不得覆盖 1/2/3。
5. **展示层**
   - 前端展示/编辑；不做 recurrence 展开，不改变硬约束。

**冲突处理**：
- 显式 `planning_mode` 与 LLM `goal_kind` 冲突 → 用显式值。
- LLM 输出与 schema 不符 → 有界重试；仍失败 → deterministic fallback。
- LLM 输出日期/时刻/series → 忽略/覆盖，不进入最终计划。

---

## 3. 目标分类体系

### 3.1 产品层：4 类 `PlanningMode`

| 类型 | 核心问题 | 例子 |
|---|---|---|
| `ONE_OFF` | 完成一次是否就结束？ | 写实验报告 |
| `RECURRING` | 同一种行为是否按明确规律重复？ | 每天背单词 |
| `PROJECT` | 是否存在有意义的内容/阶段推进？ | 学完高数 |
| `PROJECT_RECURRING` | 项目推进是否同时具有重复节奏？ | 每天学高数直到学完 |

### 3.2 LLM 层：3 类 `GoalKind` + `recurrence`

| 产品模式 | LLM `goal_kind` | `recurrence` | `work_units` |
|---|---|---|---|
| ONE_OFF | `one_off` | `null` | `[]` |
| RECURRING | `recurring` | 必填 | `[]` |
| PROJECT | `project` | `null` | 必填（数量由语义决定） |
| PROJECT_RECURRING | `project` | 必填 | 必填（数量由语义决定） |

### 3.3 判定原则

- **ONE_OFF**：单一交付物/跑腿/一次性事件；完成一次即结束。
  - 不因为标题里有日期就自动 recurring。
- **RECURRING**：同一可复用行为按规律重复；内部内容由外部 app 管理。
  - Planner 只关心「发生、频率、占用时间」。
- **PROJECT**：有明确内容/阶段推进；完成一个阶段进入下一个。
  - 必须能说出「推进结构」；否则不是 project，或需要追问。
- **PROJECT_RECURRING**：项目有内容推进，同时有重复节奏。
  - recurrence 只回答「多久推进一次」，不是拆解依据。
- **歧义**：`task_kind=LONG_TERM` 无 analysis → legacy recurring；
  有 analysis → 由 `goal_kind` 决定 project vs recurring。
- **证据不足**：优先 one_off；不要为了「看起来长期」编造 recurrence。

---

## 4. 分解就绪与追问（Decomposition Readiness）

### 4.1 核心原则

> **只有拆解能表达真实语义进展，而且现有信息足以支持该拆解时，才允许主动拆。**

否则先问，不要猜。

### 4.2 契约字段

`AnalyzedGoal` 增加：

```json
{
  "decomposition_status": "ready | needs_clarification",
  "missing_information": [
    {
      "field": "current_progress",
      "question": "你目前学到哪个章节或知识点？",
      "required": true
    }
  ]
}
```

### 4.3 图的期望行为

```
goal_analysis
      │
      ▼
ready?
 /          \
NO           YES
↓             ↓
返回补充信息   theoretical_analysis
请求           ↓
              plan_generation
```

- `needs_clarification` 时，不应进入 `theoretical_analysis` /
  `plan_generation`；应把问题返回给用户。
- `missing_information` 只放 **高影响** 未知项；低风险项可保守推断。
- 如果用户补充后再次进入，`decomposition_status` 应变为 `ready`。
- **当前实现状态**：schema、initial graph gate、API `clarification`、前端
  `ClarificationDialog` 已接线。replan graph 仍不 gate（未来再考虑）；
  partial planning 暂不支持。

### 4.4 什么时候可以推断

低风险、推断错误不会实质改变计划内容：

- 标题规范化；
- 明显的 goal_kind；
- 明显的认知负荷；
- 明显的 recurrence 语义；
- 题型/学科大致分类。

### 4.5 什么时候必须追问

高影响、猜错会改变整个计划结构：

- 当前学习进度；
- 教材/课程版本（当它决定章节序列时）；
- 用户已经掌握/跳过哪些内容；
- deadline（用户没说就不要发明）；
- recurrence frequency（用户没说就不要擅自长期化）；
- 目标考试范围；
- 项目当前完成状态；
- project 的 curriculum / 阶段列表。

### 4.6 每个模式的默认行为

| 模式 | 默认是否主动拆 | 说明 |
|---|---|---|
| ONE_OFF | 不拆成 work_units | 可给 subtasks/standards 作为 checklist，但不强行变多个 scheduler task |
| RECURRING | **不拆** | opaque execution block；外部 app 管内部 |
| PROJECT | **必须拆**，但信息不足先问 | 没有推进结构就不是 project |
| PROJECT_RECURRING | 先拆 work_units，再定节奏 | recurrence 只决定「多久推进一次」 |

---

## 5. 工作单元定义与粒度

**Work unit** 是 project / project_recurring 的一个有限、有意义、可检查的
内容/阶段单元。

### 5.1 粒度三判据

一个 work unit 应该是：

1. **可独立执行**：scheduler 可以把它作为一个安排单元；
2. **完成状态可判断**：能明确说「完成了/没完成」；
3. **完成后产生有意义的项目进展**：不是「打开教材」这种无进展动作，
   也不是「完成考研数学」这种吞掉整个项目的巨块。

### 5.2 例子

**合适**
- 学习中值定理及基础例题
- 实现 OAuth callback
- 写完论文第二章（文献综述）
- 完成实验数据整理

**太小**
- 打开教材
- 做例题 1
- 看答案
- 整理笔记（单独作为 unit 通常太小）

**太大**
- 完成考研数学
- 学完高数
- 做完整个网站

**不是语义进展**
- 学习 30 分钟
- 上午学习
- 第 3 天

### 5.3 数量规则

- **没有 prompt 最低数量**。
- 典型 2–12 个；复杂项目可以更多。
- 硬上限：`MAX_PROJECT_WORK_UNITS = 60`。
- **禁止为了凑数量制造无意义 unit。**
- 一个简单项目只有 3 个 unit 是合理的；不要为了「至少 5 个」硬加。
- 如果无法给出有意义的 unit → `needs_clarification`，不要用 goal title 充数。

### 5.4 与 subtasks / standards 的区别

- `subtasks`（goal_analysis）：一个 occurrence / work unit 内部的 checkable steps。
- `standards`（plan_generation）：具体任务内部的检查项。
- `work_units`（goal_analysis, project）：项目阶段/主题序列。
- 三者都不要跨日期枚举。
- **RECURRING 默认三者都为空**（opaque）。

---

## 6. 重复语义（RECURRING 是 opaque execution block）

### 6.1 支持的范围

- `frequency`: `daily | weekly`。
- `interval`: 整数 `>= 1`。
- `weekdays`: `0=Monday … 6=Sunday`。
  - daily：空/全 7 天。
  - weekly：指定子集；为空时默认 `start_date.weekday()`。
- `start_date` / `end_date`：inclusive。
- DAILY：`start, start+interval, ... <= end`。
- WEEKLY：以 start 所在周为锚点，每 N 周。
- 同一 series 同一 occurrence_date 恰好一个。
- 上限 `MAX_OCCURRENCES_PER_SERIES = 2000`；超过 fail closed。
- 非法范围/空 weekly/非法 interval/weekday → `RecurrenceError`。

### 6.2 RECURRING 的默认形态

Planner 只知道：

```
这件事要发生
↓
每天/每周发生
↓
预计占用 20 min
```

不知道也不管理：

```
新词多少
复习多少
遗忘曲线
错词
具体训练动作
```

因此默认：

```json
{
  "goal_kind": "recurring",
  "recurrence": {"frequency": "daily", "interval": 1},
  "work_units": [],
  "subtasks": []
}
```

- `standards` 也不应默认由模型编造。
- 除非用户明确要求 Planner 管理内部步骤，否则保持空。
- 外部 domain app 负责内部执行；Planner 只负责「排进日程」。

### 6.3 明确不支持

- monthly / custom / cron / regex 解析。
- LLM 计算天数或枚举日期。
- 「第1天…第N天」。
- 通过 title 解析重复语义。

---

## 7. 推进语义

### 7.1 RECURRING

- LLM 输出一个 reusable template。
- 代码按 occurrence date 复制 template：
  - 相同 title/description；
  - `occurrence_date = 该日期`；
  - `series_id = goal-{i}-routine/long_term`；
  - `deadline = 当天 23:59:59`；
  - `is_flexible = False`；
  - `standards = []`（默认 opaque）。
- 内容不随日期自动变化。

### 7.2 PROJECT

- LLM 输出有限、有序 work units。
- 代码生成一一对应的 drafts：
  - `task_kind = one_off`；
  - `series_id = goal-{i}-project`；
  - `occurrence_date = null`；
  - `deadline = goal.deadline`；
  - scheduler 按容量/截止日期安排。
- 项目完成 = 所有 work units 完成；不会每天自动重复。
- 没有 work units → `needs_clarification` / fail closed；不能用 goal title 充数。

### 7.3 PROJECT_RECURRING（v1 简化 + 未来契约）

**v1 当前实现**：
- work unit i ↔ occurrence i（1:1）。
- occurrence_date = 第 i 个日期；deadline = 当天。
- 多余 work units（超过日期槽位）保留为 deadline-bound 一次性 task。
- work units 少于日期槽位 → 项目提前完成，series 结束于最后使用的日期。
- 这是 v1 简化，**不是永久原则**。

**未来契约**：
```
Project
  ↓
Work Unit (e.g. 中值定理, 120min)
  ↓
Execution Chunk (e.g. 30min + 30min + 30min + 30min)
  ↓
Occurrence
```
- `work unit != occurrence`。
- 一个 work unit 可以跨多个 occurrence（chunking）。
- recurrence 决定「多久推进一次」，chunking 决定「一次做多少」。
- 当前不实现 chunking；但 prompt/契约不要写成「一个 unit = 一天」。

### 7.4 何时算完成

- ONE_OFF：唯一/少量 task 完成。
- RECURRING：生命周期到 end_date；每条 occurrence 独立完成/跳过。
- PROJECT：所有 work units 完成。
- PROJECT_RECURRING：所有 work units 完成（可能早于 deadline）。

---

## 8. LLM 权限边界

### 8.1 可以做

1. **语义解释**：objective / constraints。
2. **目标分类**：`goal_kind`（3 类）+ `recurrence`。
3. **分解就绪判断**：`decomposition_status` / `missing_information`。
4. **有意义的工作分解**：project work units；one-off subtasks。
5. **定性理论工作量**：per work unit / per occurrence。
6. **内容推进**：project work-unit 顺序。
7. **基于证据的解释**：user_situation narrative、replan 理由。
8. **候选计划**：`PlanGenerationResult.tasks`（不含日期/时刻）。

### 8.2 不可以做

- 安排日历、日期、开始/结束时刻。
- 计算天数/枚举 occurrence/写「第1天…第N天」。
- 用 regex 解析重复语义。
- 输出 `series_id`/`occurrence_date`/`series_specs`。
- 修改/覆盖显式用户数据。
- 决定硬约束是否满足；声称计划已通过 RuleEngine。
- 访问 DB/scheduler/RuleEngine。
- 丢弃 series occurrence 或把 series 变成 one-off。
- 为 project 每天复制同一个任务。
- 重新估计/改变 Level 1/2 的确定性数值。
- 编造 Level 3 completion probability。
- 编造 deadline、历史、证据、用户能力诊断。
- 用 goal title 伪造 project work unit。
- 为 recurring 编造内部 checklist（默认 opaque）。

---

## 9. 确定性代码权限边界

- **日历运算**：date arithmetic、weekday、inclusive boundaries。
- **重复规则展开**：`RecurrenceRule.occurrences()`；daily/weekly；interval；
  weekdays；2000 上限；`RecurrenceError` fail closed。
- **精确日期/时刻**：occurrence_date、start/end、scheduler slot。
- **容量约束**：daily/available limits、fixed events、high-cognitive cap。
- **冲突消解**：subject、fixed-event、buffer、same-day、HIGH spacing。
- **截止时间裁剪**：occurrence 不得晚于 occurrence_date；放不下就
  unscheduled。
- **持久化**：plans/tasks/task_standards/prediction_logs/replan_events；
  未排上的 occurrence 保留为 `PENDING`。
- **校验**：`RuleEngine` 是 hard constraints 的唯一权威。
- **Series 元数据**：series_id/index/occurrence_date/series_specs。
- **Provisional task id**：`order_index + 1`。
- **Plan 版本**：replan 创建 `v(n+1)`，旧版本 superseded，不可变。
- **Level 3 shadow**：只在 commit 后写 shadow_predictions，不影响计划。
- **Clarification gate**：当 `decomposition_status=needs_clarification` 时，
  图应在 `goal_analysis` 后分流，而不是继续规划（当前为待接线状态）。

**口诀**：
> LLM proposes; deterministic materializes; scheduler places;
> RuleEngine validates; Service persists.

---

## 10. 现有结构化数据负责

| 数据 | 来源 | LLM 的角色 |
|---|---|---|
| 用户提供日期 | `GoalInput.start_date/deadline` | 读取；不发明/改写 |
| 显式重复规则 | `planning_mode`、`recurrence_*` | 读取；优先遵循 |
| 显式时长 | `estimated_minutes`、`daily_target_minutes` | 读取；作为工作量/每次投入 |
| 已完成工作 | current_plan、completed titles、progress | 读取；不重排已完成 |
| 确定性用户模型 | Level 1 trait + Level 2 state | 读取为 evidence；不重估/不诊断 |
| 固定事件 | fixed_events | 读取；不安排到其中 |
| 用户偏好 | PreferenceInput / UserPreferences | 读取；不覆盖 |
| 当前计划/反馈 | current_plan、recent_feedback、progress | 读取；replan 保留未完成 |
| 目标元数据 | goal_type、task_kind、subject、task_type、target_* | 读取；兼容/上下文 |

**注意**：
- 「结构化数据负责」= 事实由系统/用户提供，LLM 只解释。
- 显式 `planning_mode` 优先于 LLM 分类。
- 缺失时给保守 proposal，不编造事实。

---

## 11. 不确定性策略

| 情况 | 策略 |
|---|---|
| 缺 start/deadline | recurring/project 用 request window（默认 today+13）；说明 |
| 缺 recurrence | 显式 weekdays 子集 → weekly；空/7 → daily；仍无 → 不擅自长期化 |
| 信息不足（项目进度/范围/教材） | `decomposition_status=needs_clarification` + `missing_information`；不拆 |
| 非法 recurrence | `RecurrenceError`，fail closed；不静默回退 |
| occurrence > 2000 | fail closed；不截断 |
| work units > 60 | fail closed；不截断 |
| project 无 work units | `needs_clarification`；deterministic fallback fail closed；**不用 goal title 充数** |
| LLM JSON/schema 失败 | 有界重试；仍失败 → deterministic fallback；degraded |
| LLM 不可用 | deterministic fallback；warnings |
| 分类歧义（LONG_TERM） | 有 analysis → 用 analysis；无 → legacy recurring |
| 容量不足 | scheduler unscheduled；persist PENDING；不丢 occurrence |
| 显式数据与 LLM 冲突 | 显式数据优先 |
| 证据不足 | confidence 低；narrative 说明；不编造 |
| Level 3 缺失 | 不发明；shadow-only |
| 计划无法通过硬校验 | repair 有界；仍失败 → best effort + repair_exhausted |
| 重复展开/持久化异常 | fail closed / 明确错误 |

**原则**：
> Fail closed > silently wrong；Never truncate a series；
> Never invent dates/times/deadlines/history；Confidence ≠ validation。

---

## 12. 证据策略

### 12.1 可用证据

- Level 1 traits（稳定）。
- Level 2 fatigue/stress/energy/efficacy（pre-task state）。
- Memory：semantic / episodic / procedural。
- Progress：完成率、分钟、任务状态。
- Feedback：completion、stress、energy、delay、free text。
- Current plan：未完成/已完成、series 状态。
- Goal metadata：显式日期/重复/时长/优先级/subject。
- Fixed events：课程/考试/忙碌块。

### 12.2 使用规则

- 证据只用于解释与候选决策，不是 hard constraint。
- 引用具体证据；例如「过去 5 天有 3 天完成率低于 40%」。
- 不诊断；不把 profile 当能力定论。
- 不重新估计/改变确定性数值。
- 不编造历史、deadline、完成概率。
- Level 3 shadow；缺失不补。
- `prediction_source` 必须真实。
- Replan 只保留未完成；不重排已完成。
- 证据冲突时优先显式数据和最近反馈；在 notes 说明。

---

## 13. Level 1 / Level 2 的正面权限矩阵

### 13.1 核心思想

- **Level 1**：影响长期规划策略。
- **Level 2**：影响当前执行负荷。
- 两者都不能改变「目标是什么/内容是什么/截止日期/重复规则」。

### 13.2 权限矩阵

| 内容 | Level 1 | Level 2 |
|---|---:|---:|
| goal_kind | ❌ | ❌ |
| recurrence | ❌ | ❌ |
| 用户目标内容 | ❌ | ❌ |
| work-unit curriculum | ❌ | ❌ |
| deadline | ❌ | ❌ |
| estimated theoretical workload | ❌ | ❌ |
| predicted duration | ✅ deterministic | ✅ deterministic |
| 当日 workload | 轻微 | ✅ |
| 高认知任务密度 | 轻微 | ✅ |
| task duration / chunk size | 可影响 | ✅ |
| replan aggressiveness | 可影响 | ✅ |
| explanation | ✅ | ✅ |

### 13.3 例子

- Level 2 fatigue 高：
  - 允许：高数 90min → 45min chunks；
  - 允许：降低当天高认知任务总量；
  - 不允许：删除高数目标；
  - 不允许：改学英语。
- Level 1 开放性高：
  - 允许：更愿意给探索性/多样化任务；
  - 不允许：擅自增加数学竞赛内容。

---

## 14. 共享不变量

1. LLM 不输出日期/时刻。
2. LLM 不输出 `series_id`/`occurrence_date`/`series_specs`。
3. LLM 不按日期枚举 occurrence；不写「第1天…第N天」。
4. Provisional task id = `order_index + 1`。
5. 同一 series 同一 occurrence_date 最多一个。
6. occurrence_date 在 `[start,end]` 内（inclusive）。
7. occurrence 的 scheduled_date == occurrence_date；不漂移。
8. recurring 只支持 daily/weekly；interval >= 1；weekdays 0..6。
9. `MAX_OCCURRENCES_PER_SERIES = 2000`。
10. project work units 有限、有序；典型 2–12；硬上限 60；无最低数量。
11. project 不每天复制同一任务；project_recurring 才做推进配对。
12. `series_specs` 由 deterministic 层生成。
13. RuleEngine 是 hard constraints 唯一权威；scheduler 只产生候选。
14. Scheduler 不调用 LLM。
15. Agents 不访问 DB；数据由 application layer 注入。
16. Repositories 不 commit；services 拥有事务。
17. Plan 版本不可变；replan 创建 v(n+1)。
18. 未排上的 occurrence 保留 PENDING，不静默丢弃。
19. Level 3 shadow-only。
20. `prediction_source` 必须真实。
21. start/end inclusive。
22. 缺 deadline 用 request horizon（默认 today+13）。
23. 显式用户数据优先于 LLM 推断。
24. Confidence 不是校验结果。
25. RECURRING 默认 opaque：subtasks/work_units/standards 为空。
26. 信息不足先 `needs_clarification`，不用 goal title 伪造 unit。
27. Theoretical workload 是 work-unit-level / per-occurrence，不是 goal-level 总量。
28. project_recurring 的 unit↔occurrence 1:1 是 v1 简化，未来是 unit→chunk→occurrence。

---

## 15. 每个节点的输入/输出职责

### 15.1 Initial workflow

```
START
 -> load_context
 -> goal_analysis
 -> [ready?] --NO--> clarification request -> END/USER
      |
     YES
      ↓
 -> theoretical_analysis
 -> user_situation_analysis
 -> plan_generation
 -> rule_validation
 -[repair loop]-> preview
 -> [adjust -> plan_generation | confirm -> plan_finalization] -> END
```

| 节点 | 类型 | 输入 | 输出/state |
|---|---|---|---|
| `load_context` | deterministic | user_id, plan_id, overrides | `user_context`, `current_plan` |
| `goal_analysis` | LLM (`goal_analysis.md`) | goals, user_profile, execution_weight | `goal_analysis: GoalAnalysisResult`（含 status/missing_information） |
| clarification gate | deterministic | `goal_analysis` | 若 `needs_clarification`，返回问题；不进后续 |
| `theoretical_analysis` | LLM (`theoretical_analysis.md`) | goals, goal_analysis, user_profile | `theoretical_analysis`（per work unit / per occurrence） |
| `user_situation_analysis` | deterministic numbers + optional LLM narrative | user_context, user_model, estimate, progress | `user_situation` + narrative |
| `plan_generation` | LLM (`initial_plan.md`/`replanning.md`/`adjustment.md`) + deterministic `_materialize` | goals, goal_analysis, theoretical, user_situation, preferences, preview/current_plan | `plan_draft`（tasks + series_specs） |
| `rule_validation` | deterministic | plan_draft, preferences, goals | candidate, rule_validation |
| `plan_repair` | deterministic | plan_draft, violations | updated plan_draft, repaired_plan |
| `preview` | deterministic | plan_draft, candidate, validation | preview |
| `plan_finalization` | deterministic | plan_draft, request, validation | final_plan |

### 15.2 Replan workflow

```
START -> load_context -> process_feedback -> adjustment_decision
 -> adjustment_router
    |- NO_CHANGE -> END
    |- MICRO_ADJUST -> micro_adjustment -> rule_validation -> plan_finalization
    |- FULL_REPLAN -> goal_analysis -> ... -> plan_finalization
```

`replanning.md` 不重新发明 curriculum；只改变执行策略。

### 15.3 Prompt 输入/输出速查

#### `goal_analysis.md` → `GoalAnalysisResult`

输入：`goals`, `user_profile`, `execution_weight`。

输出：
```json
{
  "goals": [{
    "goal_id": 1,
    "title": "...",
    "objective": "...",
    "constraints": ["..."],
    "goal_kind": "one_off | recurring | project",
    "recurrence": {"frequency": "daily|weekly", "interval": 1, "weekdays": [0,1,2,3,4,5,6]},
    "work_units": [{"title": "...", "description": "...", "estimated_minutes": 60}],
    "subtasks": [],
    "decomposition_status": "ready | needs_clarification",
    "missing_information": [{"field": "...", "question": "...", "required": true}]
  }],
  "summary": "...",
  "confidence": 0.5
}
```

#### `theoretical_analysis.md` → `TheoreticalAnalysisResult`

输入：`goals`, `goal_analysis`, `user_profile`。

输出：one item per work unit for project/project_recurring;
one item per recurring occurrence; one item per one-off.

```json
{
  "items": [{
    "title": "...",
    "goal_id": 1,
    "work_unit_index": 0,
    "learning_content": "...",
    "subtasks": [],
    "video_minutes": 0,
    "reading_minutes": 0,
    "practice_minutes": 0,
    "total_minutes": 0,
    "difficulty": 3.0,
    "cognitive_load": "high|medium|low|restorative"
  }],
  "total_theoretical_minutes": 0,
  "overall_difficulty": 3.0,
  "cognitive_load": "medium",
  "confidence": 0.5
}
```

#### `user_situation.md` → `UserSituationNarrative`

输入：`user_context`, `user_model`, `situation_estimate`, `progress`。
输出：`{"narrative": "...", "confidence": 0.5}`。数值不改。

#### `initial_plan.md` → `PlanGenerationResult`

输入：`goal_analysis`, `theoretical_analysis`, `user_situation`,
`user_model`, `goals`, `preferences`。
输出：tasks（不含日期/时刻；series_specs 由代码填）。

#### `replanning.md` → `PlanGenerationResult`

输入：`replan_reason`, `planning_context`, `user_model`,
`adjustment_decision`, `current_plan`, `progress`。
规则：保留未完成；保留 series/template/curriculum；不重新枚举日期；
不把 series 变 one-off。

#### `adjustment.md` → `PlanGenerationResult`

输入：`preview`, `user_adjustment`, `preferences`, `user_model`,
`adjustment_count`。
规则：只改用户明确要求的可变属性；保持 occurrence/series；
不改 goal semantics/recurrence；不合并/改日期。

---

## 16. 好示例 / 坏示例

### 16.1 RECURRING（opaque）

**好**
```json
{
  "goal_kind": "recurring",
  "recurrence": {"frequency": "daily", "interval": 1, "weekdays": []},
  "work_units": [],
  "subtasks": [],
  "objective": "背考研英语单词",
  "constraints": ["每天 20 分钟"],
  "decomposition_status": "ready"
}
```
plan：一个 reusable template；代码展开 occurrence；standards=[]。

**坏**
- 输出「过一遍词表 / 标记生词 / 复习昨日生词」作为 subtasks/standards。
- 输出 7/249 个「第1天…第N天」。
- 写日期/时刻。
- 让 LLM 计算 249 天。

### 16.2 PROJECT

**好**
```json
{
  "goal_kind": "project",
  "recurrence": null,
  "work_units": [
    {"title": "极限", "description": "...", "estimated_minutes": 120},
    {"title": "导数", "description": "...", "estimated_minutes": 120},
    {"title": "积分", "description": "...", "estimated_minutes": 120}
  ],
  "subtasks": [],
  "objective": "在 2027-07-01 前学完高等数学",
  "decomposition_status": "ready"
}
```
3 个 unit 也可以；不要为了 5 个硬加。

**坏**
- 把「学习高等数学」复制 249 次。
- 输出 1 个 unit「学高数」吃掉整个项目。
- 输出 `recurrence.daily`（除非用户明确要每天推进）。
- 输出日期/时刻。

### 16.3 PROJECT_RECURRING

**好**
```json
{
  "goal_kind": "project",
  "recurrence": {"frequency": "daily", "interval": 1},
  "work_units": [
    {"title": "极限", "description": "...", "estimated_minutes": 60},
    {"title": "导数", "description": "...", "estimated_minutes": 60},
    {"title": "积分", "description": "...", "estimated_minutes": 60}
  ],
  "subtasks": [],
  "objective": "每天学高等数学直到学完",
  "decomposition_status": "ready"
}
```
v1：unit i ↔ occurrence i；未来：unit → chunk → occurrence。

**坏**
- `goal_kind="project_recurring"`（schema 没有）。
- 只给 recurrence，不给 work_units。
- 每天复制同一个 unit。
- 把 1:1 写成永久原则。

### 16.4 信息不足

**好**
```json
{
  "goal_kind": "project",
  "objective": "30 天完成高数阶段学习",
  "work_units": [],
  "decomposition_status": "needs_clarification",
  "missing_information": [
    {"field": "current_progress", "question": "你目前学到哪个章节或知识点？", "required": true},
    {"field": "curriculum", "question": "你使用的教材/课程范围是什么？", "required": true}
  ]
}
```

**坏**
- 用「学高数」作为唯一 work unit，假装 ready。
- 猜一个 curriculum。
- 直接进入 plan generation。

### 16.5 P0 反例（禁止）

```
第1天 10:15-10:35
第2天 11:00-11:20
...
第7天 14:45-15:05
```
全部落在同一个自然日。

**错在**：recurring 被当成 7 个 one-off；无 occurrence_date；
scheduler 贪心塞进同一天；「第N天」只是 title。

**正确**：goal_analysis 输出 recurring + daily；initial_plan 一个 template；
RecurrenceRule 展开；scheduler 按 occurrence_date 放置；RuleEngine 校验。

---

## 17. 当前实现状态与后续顺序

### 17.1 已落地

- `PlanningMode` 4 值（API/DB/UI）；LLM `GoalKind` 3 值 + `RecurrenceSpec`。
- `work_units` / `recurrence` / `series_specs` / `RecurrenceRule` /
  `RecurrenceConsistencyRule`。
- RECURRING opaque：归一化清空 `subtasks/work_units`；materializer 清空
  `standards`。
- `AnalyzedGoal.decomposition_status` / `missing_information` schema 字段。
- request-level atomic clarification gate（initial graph）+ API
  `clarification` + 前端简单 text-input dialog。
- 用户补充的 `clarifications` 作为独立 provenance 进入 `GoalInput`，不拼接
  title/description。
- `TheoreticalItem.goal_id` / `work_unit_index` schema 字段；
  deterministic workload estimator 已按 work unit / per occurrence 产出。
- PROJECT 无 work units 时不再用 goal title 伪造 unit；fail closed。

### 17.2 尚未接线 / 后续

1. **Replan clarification gate**：initial graph 已接线；replan graph 仍不 gate。
   partial planning 暂不支持。
2. **`theoretical_analysis.md` 的 LLM 输出**：schema/fallback 已支持 per
   work unit；prompt 已做最小更新，但仍需在正式重写时做 golden-case 测试。
3. **PROJECT_RECURRING chunking**：当前仍是 1:1；未来 `Work Unit →
   Execution Chunk → Occurrence`。未实现。
4. **Curriculum Provider**：未来可插拔模块；现在不把 goal analysis 做成
   全世界课程知识库。
5. **六份 prompt**：本 spec 稳定后再写；`goal_analysis.md` 第一份，最值得
   golden-case 测试。

### 17.3 推荐的实现顺序

1. （已完成）request-level atomic clarification gate + API/前端契约。
2. 用 golden cases 重写 `goal_analysis.md`（含 ready / needs_clarification）。
3. 重写 `theoretical_analysis.md`（per work unit / per occurrence）。
4. `initial_plan.md` 变薄：只生成 execution candidates。
5. `adjustment.md` / `replanning.md`：只改执行策略，不重写 curriculum。
6. 最后再考虑 PROJECT_RECURRING chunking。

---

## 18. 一句话总结

**LLM 负责「理解目标、判断信息够不够、拆出有意义的 work units」；
deterministic code 负责「日期、occurrence、容量、校验、持久化」。
RECURRING 默认是不透明的执行块；PROJECT 必须有语义 work units；
信息不足先追问，不要用 goal title 糊一个假 unit；
work unit ≠ occurrence（v1 的 1:1 只是临时简化）。**
