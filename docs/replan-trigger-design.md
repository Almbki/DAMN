# 后端触发重排机制设计（Replan Trigger Design）

> 回答：**后端触发的重排到底由什么执行？用完成率？微调模型？画像？RAG？** 以及两个未决问题：
> **(1) 已排好计划时用户新增任务怎么处理；(2) 用户没做完该怎么补。**
> 配套：`docs/architecture-overview.md`（§4.2 反馈链路）、`docs/product-painpoints.md`。

---

## 0. 结论速览（TL;DR）

1. **不要用 LLM / 微调模型 / RAG 来做“是否重排”的判定。** 触发是低维、廉价、代价敏感的二分类决策，应该用**可校准的确定性打分 + 阈值**。LLM 只用来**生成/修复计划**，RAG 只用来**给生成/修复提供依据**。
2. **完成率不是唯一信号，但也不该被抛弃**——它是“结果信号”。需要一个 **混合触发集**：事件 + 周期 + 滑移(slippage) + 画像状态。
3. 真正的关键不是“用哪个信号”，而是**仲裁层（arbiter）**：统一打分 → 冷却/滞后/日预算/最小改进门槛 → 决定 `NO_CHANGE / MICRO_ADJUST / FULL_REPLAN`。
4. 新增任务：**最便宜优先的决策阶梯**（空隙直插 → 局部修复 → 全量重排），把“稳定性”作为目标项，避免日程抖动。
5. 未完成 backlog：**容量优先的 roll-forward + 决策树**（habit 只滚下一次 / 硬 DDL 升级并 re-break / 反复推迟→decay 或显式 drop），并设 rollover 上限防雪崩。

---

## 1. 现状：两条触发路径的**精确**逻辑

后端目前有**两个互不相干**的触发路径。

### 路径 1：手动重排 `POST /plans/{id}/replan`
```
check_eligibility（仅按用户冷却：距最近 ReplanEvent ≥ SCHEDULER_MIN_REPLAN_INTERVAL_HOURS）
  → PlanService.replan_with_agent → 图 B → 必产生 v(n+1)，旧版 superseded，trigger_type = MANUAL
```
- 唯一的门禁是**用户级冷却**，没有任何严重度判断。

### 路径 2：反馈驱动 `POST /plans/{id}/feedback` → `PlanService.process_feedback_cycle` → 图 B
路由由 `app/agent/router.py::AdjustmentRouter.decide` 决定，规则如下（**覆盖条件永远优先于 ML 信号**）：

| 条件 | 结果 | 位置 |
| --- | --- | --- |
| 无当前计划 | FULL_REPLAN | `router.py` |
| **任意非空用户备注(free_text)** | **FULL_REPLAN** | `router.py` |
| `days_elapsed ≥ 2` 且 `completion_rate < 0.3` | FULL_REPLAN | `router.py` |
| `adjustment_count ≥ max_consecutive_micro_adjustments`（默认 2） | FULL_REPLAN | `router.py` |
| 画像升级（只升不降）：5 天全 < 0.40 → FULL_REPLAN；近 2 天 < 0.60 或 `duration_bias > 0.50` → MICRO_ADJUST | 升级 | `profile_service.replan_decision_for` → `domain/profile/engine.py::replan_decision` |
| 否则依据 `ml_prediction`（mock）→ 三选一 | — | `router.py` |

- **路径 2 不受冷却限制**：`check_eligibility` 只用于在响应里*报告*，不拦截。
- 持久化：只有当 `final_plan` 存在时才落 v(n+1)；`micro_adjust` 记 `FEEDBACK_TRIGGERED`，**其余全量重排被误记为 `MANUAL`**。

---

## 2. 现状诊断

1. **反馈路径无冷却/滞后/预算** → 每次 check-in 都可能产生新版本，版本链抖动、用户信任受损。（唯一门禁只在手动路径。）
2. **自由文本 = 无条件全量重排**：一句“今天有点累”就重建整份计划。应让它进入分类器，而不是短路。
3. **两套并行决策系统、阈值不一致**（router 的 0.3/2天 vs 画像的 0.40×5天、0.60×2天、bias>0.5），且“只升不降”的合并让分歧不可见。
4. **`trigger_type` 误标**（反馈全量重排记为 MANUAL）→ 污染本该用于校准的 `replan_events`。
5. **无最小改进门槛**：可能重排出与旧计划几乎一样的计划；而且 `changed_task_ids` 目前返回新版本*全部*任务，**连“是否改进”都无法度量**。
6. **主信号是 mock**：`ml_prediction` 是统计 mock，实际起决定作用的是覆盖条件。

---

## 3. 回答“到底由什么执行”（信号取舍）

### 3.1 信号分类（必须都有，但角色不同）

| 信号类 | 例子 | 性质 | 缺点 |
| --- | --- | --- | --- |
| **结果/反馈信号** | 完成率、计划 vs 实际滑移 | 事后检测“已经失败” | 滞后、噪声大 |
| **输入/事件信号** | 新增任务、改截止、日历冲突、任务完成 | 事前规避 | 事件风暴、日历抖动 |
| **状态信号** | 画像 EWMA、精力/压力、duration_bias | 个性化 | 反馈回路、隐私 |

关键不对称：**结果信号检测失败，事件/状态信号预判失败**——成熟系统两者都要。

### 3.2 完成率 / 微调模型 / 画像 / RAG 的结论

- **完成率**：保留，作为打分的一项（`low_completion_streak`），但**不单独决定**。
- **微调模型**：**现在不要做**。触发决策需要**标签**（“这次重排到底该不该发生”），当前数据规模远不够；先做可解释的打分，同时把每次决策记录成训练集（见 §4 的新表），将来再上小型 GBDT/逻辑回归。微调 LLM 做触发是最后阶段的事，不是起点。
- **画像**：作为**特征/权重与个性化冷却**（不同人容忍抖动的程度不同），而不是直接决策；注意冷启动用先验、随数据增长逐步让位给结果信号。
- **RAG**：**不要用于触发**（低维数值决策，检索延迟与非确定性都是负价值）。RAG 应该用于**计划生成/修复**：检索用户历史计划、`TaskStandard` 模板、相似情境作为 few-shot 依据。落地时优先复用现有 `memory_retriever` + `agent_memories`，先做“结构化检索 + 过滤”，不必先向量库。

### 3.3 混合触发集 + 仲裁（行业标准做法）

```
trigger_score = w_event * 事件紧急度
              + w_slip  * 归一化滑移
              + w_dead  * 截止风险
              + w_state * 画像状态分
        (未来)  + w_ml    * 校准后的模型概率
```
- **阈值**：`score > T_hi` 自动执行；`[T_lo, T_hi)` 只**建议**不自动改。
- **滞后(hysteresis)**：需连续两次满足才触发；进入/退出用不同阈值。
- **冷却(cooldown)**：按用户，不是按计划（现有 `ReplanEventRepository.get_latest_for_user` 正是正确原语）。
- **日预算**：每人每天自动重排上限（如 3~5 次），超出降级为“建议”。
- **最小改进门槛**：预期收益须超过“稳定性代价(抖动成本)”。

> 参考实现：AWS EC2 Auto Scaling 的 cooldown 就是“动作后等待稳定再允许下一次”，是很好的工程类比。

---

## 4. 目标架构（与现有代码对齐）

### 4.1 新增模块

| 模块 | 职责 |
| --- | --- |
| `app/domain/replan/policy.py`（新） | **纯函数**：`signals → score → route`；含滞后/最小改进的阈值常量。复用 `engine.py::replan_decision` 的阈值作为初始权重。 |
| `app/application/services/trigger_service.py`（新） | **仲裁器**：收集信号 → 调 policy → 依次应用门禁（冷却→日预算→最小改进）→ 决定是否执行。 |
| `app/agent/...` 图 B | **不改图**。仲裁器决定后调用现有的 `process_feedback_cycle` / `replan_with_agent`，不再新增第三条重排路径。 |

### 4.2 新增数据

- 新表 **`replan_trigger_evaluations`**：
  `id, user_id, plan_id, source(event|periodic|slippage|state|manual), score, route_decided, gates_hit(json), acted(bool), created_at`
  → **这就是未来训练“是否该重排”分类器的数据集**，不是可选项。
- `ReplanTriggerType` 扩展：新增 `AUTO_SLIPPAGE`、`AUTO_PERIODIC`、`FEEDBACK_FULL`，修正误标。

### 4.3 触发源接入

- **事件**：`FeedbackService.submit_feedback` 不再直接调 `process_feedback_cycle`，改为向仲裁器发 `TriggerSignal`（保持反馈提交快、可单测）。
- **周期**：每日一次 sweep（后台任务或当日首个请求触发）评估所有 active plan。
- **滑移**：`sum(未完成任务的预测时长) / 剩余容量 > 1.2`，或目标临近截止。
- **状态**：画像 EWMA / `duration_bias`。

### 4.4 门禁顺序（仲裁器内）

```
1. 用户级冷却（扩展到现在的手动+反馈两条路径）
2. 日预算（新配置项）
3. 最小改进门槛：把图 B 结果当“候选”，与旧计划 diff（修好 changed_task_ids / 复用 diff_days），
   改动 < 阈值则丢弃并记录
```

### 4.5 与现有机制的关系

- 执行时复用 `PlanService.process_feedback_cycle` / `replan_with_agent`，**不新建重排路径**。
- Router 的覆盖条件降级为**安全底线**（无计划、用户显式请求），其余交给打分。
- SSE：自动重排静默产生新版本；通过现有 `GET /plans/{id}/changes` 呈现，并可在下次连接时推一个 `replan` 事件（回放基建已具备）。

> 迁移成本估计：新模块 + 新表 + 改写 `feedback_service` ≈ 2~3 天；policy/gates 都是纯函数，可完全按现有风格单测。

---

## 5. 未决问题 1：**已排期时用户新增任务**

核心权衡是**质量 vs 稳定性**：过度重排会造成“日程抖动(nervousness)”，即使目标更优也伤信任。动态调度理论（Vieira 2003；Ouelhadj & Petrovic 2008）给出的策略从便宜到昂贵：不动 → 右移(right-shift) → 局部修复 → 匹配修补(match-up) → 全量重建。

### 5.1 情况分类（按“最便宜优先”判定）

| 情况 | 条件 | 动作 |
| --- | --- | --- |
| **C1 有空隙** | 存在时长足够、且在截止前的连续空隙（含工作时窗） | **直接插入**（best-fit：选最小的够用空隙），其他任务不动 |
| **C2 局部可挪** | 无单个空隙，但邻任务可在自身松弛内移动 | **局部修复**（只右移最少必要集合） |
| **C3 固定事件冲突** | 会议/硬日程挡住可行时段 | 把固定事件当**硬约束**绕开；实在不行允许溢出到非工作时段，或**询问用户** |
| **C4 改变关键路径/依赖** | 新任务是前置或后继 | **级联平移**（依赖链）；用 RCPSP 优先级规则(最小松弛 LFT/MSLK) |
| **C5 优先级更高** | 新任务压过已排任务 | **抢占/驱逐**：把优先级最低、最灵活的任务挪后，最小化偏差 |
| **C6 使计划不可行** | 修复后仍无法满足某截止 | **显式取舍**：拆分 / 延后低优先级 / 向用户暴露 trade-off；**绝不静默违约** |

### 5.2 决策阶梯（推荐落地顺序）

```
1. C1 → best-fit 空隙直插（不动别人）
2. C2/C3 → 在 [今天, +7天] 移动窗口内做局部修复/match-up，最小化总偏差，尊重固定事件
3. C4/C5 → 依赖级联 或 优先级驱逐
4. C6 → 向用户暴露取舍（自动模式下：拆分/延后最低价值任务）
5. 仅当局部修复未过“最小改进门槛”时，才回退到 Full regeneration
```

### 5.3 算法/模式

- **空隙启发式**：first-fit / **best-fit** / worst-fit（best-fit 减少碎片化，默认）。
- **列表调度 + 优先级规则**：EDD（最早截止优先）、**最小松弛**、SPT/LPT。
- **RCPSP 优先级**（有依赖时）：LFT、MSLK。
- **右移/局部重排**：只从插入点向后、限定时间窗。
- **match-up scheduling**：局部修补后找“重新汇合点”，**最小化改动数**——最贴合“插一个新任务”。
- **插入代价最小化**（来自车辆路径的 cheapest-insertion 思路）：对每个可行位置算增量代价（延迟+抖动），取最小。

> 落地注意：插入/修复必须维护 **临时 id = `order_index + 1`** 契约，保证与 SSE/落库路径一致；新增任务要产生新的 provisional id。

---

## 6. 未决问题 2：**未完成任务（backlog）怎么补**

### 6.1 策略菜单

| 策略 | 说明 | 适用 |
| --- | --- | --- |
| Roll forward | 滚到次日/次周，保持优先级 | 中等优先级、仍相关、有截止 |
| Decay / expire | 随时间降权，N 天后自动归档 | 可有可无、过期想法 |
| Re-break-down | 拆更小 / 缩短首个 session | **反复被回避的大任务（往往真问题是“太大”）** |
| Drop | 显式删除并给原因 | 低价值 backlog，保留信任 |
| Escalate (aging) | 随年龄/临近截止升权 | 承诺类、阻塞他人的任务 |
| Batch triage | 周期性人工清理 | 防无限增长 |

**产品观察**：Sunsama = 容量优先 + 每日仪式（5PM shutdown）；Reclaim = roll-forward 自动重排（连 habit 也只重排“下一次”，不累积错过的历史）；Motion = 连续重排 + 分块(chunking) + 硬/软截止；Todoist = 区分 due/deadline，靠 weekly review 防 backlog 腐烂。

### 6.2 每个未完成任务的处理（决策树）

```
habit（习惯）        → 只重排“下一次”，绝不累积“你错过了 12 天”
阻塞/硬截止          → 升级 + 若预估 > 剩余容量则 re-break
被推迟 ≥2~3 次
  或 低完成概率+低价值 → 显式 drop / decay（带原因）
其余                 → roll forward（但受 rollover 上限约束）
```

判定信号：逾期天数/年龄、截止硬度、**被推迟次数**、预估工作量 vs 剩余容量、依赖关系、是否习惯、预测完成概率、用户精力状态。

行为学依据：拖延可用**现时偏差/时间折扣**建模（Sci Rep 2024；Nat Commun 2022）——**把近期动作变小、变具体**（降低即时成本）比“更用力提醒”更有效，这正对应 **re-break-down**。

### 6.3 防雪崩 / 防内疚掉线

- **容量优先**：排入的预估总时长 ≤ 可用容量（backlog 雪崩多是**过量排期**的 bug，不是动力问题）。
- **限制在制品(WIP)**：每日自动排入任务设上限，backlog 可见但有界。
- **rollover 上限 + 强制 triage**：carry 超过阈值就停止静默滚动，要求一键 “keep / split / drop”。
- **decay + 显式 drop**：避免“幽灵清单”无限增长。
- **habit ≠ backlog**：只滚下一次。
- **文案中性化**：避免用红色“逾期”计数施压，用“已移到明天”这类中性语（正向框架，降低掉线）。
- **backlog 层面的阻尼**：backlog 超阈值时**不要**逐项触发重排（会放大抖动），改为每日边界批量 triage。

---

## 7. 分阶段落地路线图

| 阶段 | 内容 | 依赖 |
| --- | --- | --- |
| **P0（先修 bug）** | 修 `changed_task_ids`（按天集合 diff）、`get_plan(0)`、horizon 13/14、`trigger_type` 误标 | 无 |
| **P1（仲裁器 MVP）** | `domain/replan/policy.py` + `trigger_service.py` + `replan_trigger_evaluations` 表；冷却应用到反馈路径；去掉“自由文本无条件全量重排”；引入滞后+日预算 | P0 |
| **P2（新增任务阶梯）** | C1 空隙直插 + C2/C3 局部修复；稳定性作为目标项 | P1 |
| **P3（backlog 决策树）** | roll-forward + decay/drop + habit 规则 + rollover 上限 | P1 |
| **P4（RAG 生成/修复）** | 复用 `memory_retriever` 检索历史计划/标准，注入 plan_drafter/repair | P1 |
| **P5（学习型触发）** | 用 `replan_trigger_evaluations` 训练小型 GBDT 作为打分的一项（可选，数据够才做） | P1+数据 |

---

## 8. 参考文献（节选）

- Vieira, Herrmann & Lin (2003). *Rescheduling Manufacturing Systems.* J. Scheduling. doi:10.1023/A:1022235519958
- Ouelhadj & Petrovic (2008). *A survey of dynamic scheduling in manufacturing systems.* J. Scheduling. doi:10.1007/s10951-008-0090-8
- Bean et al. (1999). *Match-up scheduling under a machine breakdown.* EJOR. doi:10.1016/S0377-2217(97)00396-2
- Graham (1969). *Bounds on Multiprocessing Timing Anomalies.* SIAM. doi:10.1137/0117039
- Barnett et al. (2024). *Seven Failure Points When Engineering a RAG System.* arXiv:2401.05856
- *Temporal discounting predicts procrastination in the real world.* Sci Rep (2024). doi:10.1038/s41598-024-65110-4
- *A neuro-computational account of procrastination behavior.* Nat Commun (2022). doi:10.1038/s41467-022-33119-w
- AWS. *Scaling cooldowns for EC2 Auto Scaling.*（冷却/滞后工程类比）
- 产品：Motion Help Center、Reclaim.ai features、Sunsama、Todoist Help。
