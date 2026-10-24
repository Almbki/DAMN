# DDSR-V1 缺陷、风险与小优化方案（中文版）

> 本文只做方案推荐，**不改代码**。  
> 结论先行：V1 目前是“机制/契约就绪”，不是“真实数据精度就绪”。  
> 最值得优先做的不是加深模型，而是：**接真实 LLM、做小规模 pilot、校准 uncertainty、补产品集成**。

---

## 0. 优先级结论

### 建议马上做（P0，1–2 周）

1. 接入真实 LLM client，建立 100–200 条人工标注的 evidence gold set。
2. 做 20–30 人 × 14–28 天的小规模 pilot，收集真实 task log + reflection。
3. 校准 uncertainty：看 50%/80%/95% 区间的实际覆盖率，计算 CRPS。
4. 在发送给 LLM 前做 PII 脱敏，并加隐私/保留策略。
5. 加一个 evidence verifier（第二道检查），降低 LLM 误标。

### 建议下一步做（P1，2–4 周）

6. 证据聚类与跨状态折扣，避免同一句话同时把 fatigue 和 stress 推高。
7. 行为指标缺失偏差处理：增加 missingness flag、duration-weighted goal attainment。
8. 冷启动分层 warm-up，而不是永远 0.5/0.25。
9. 接 DAMN 的 service / repository / API，把模型真正用起来。
10. 加 drift monitor：监控 prediction error 的 EWMA。

### 不建议现在做

- 深度时序网络（LSTM/Transformer）——没有足够 longitudinal 数据。
- Trait → State 固定权重——Level 1 明确冻结，V1 也不该自创。
- 把 screen time 直接解释成拖延/疲劳——没有证据，也容易造成伤害。
- 在线个性化 transition learning——数据量不够，容易过拟合。

---

## 1. 当前模型的主要缺陷

| # | 缺陷 | 影响 | 严重度 | V1 是否可接受 |
|---|---|---|---|---|
| 1 | 没有真实长期数据验证 | 不知道 MAE/CRPS/区间覆盖率 | 高 | 可接受，但必须标注 |
| 2 | 真实 LLM 语义质量未验证 | 可能漏抽/误标 evidence | 高 | 可接受，但上线前必须测 |
| 3 | uncertainty 未校准 | 区间可能过窄或过宽 | 高 | 可接受，但 pilot 后要调 |
| 4 | 同一句话可能同时产生 fatigue + stress 证据 | 相关证据被当成独立证据，状态被双重推高 | 中 | 可接受，但建议加折扣 |
| 5 | 拖延识别偏保守 | 用户不明确说“拖延”时会漏 | 中 | 可接受（宁可漏，不可误判） |
| 6 | initiation rate 以有日志任务为条件 | 用户漏记任务时，指标可能偏高 | 中 | 可接受，已有 planned_coverage |
| 7 | 冷启动固定 0.5/0.25 | 对极端用户可能不友好 | 中 | 可接受，V1 不应伪装个体化 |
| 8 | ρ/q/κ/weights 未估计 | 参数是工程初始化，不是数据拟合 | 中 | 可接受，但要做敏感性分析 |
| 9 | fatigue 与 stress 没有协方差 | 两个状态可能不自然地独立变化 | 中 | 可接受，V1 保持简单 |
| 10 | 只有日级粒度 | 无法区分上午/下午/晚上的状态变化 | 中 | 可接受，DRM 本身就是日级回顾 |
| 11 | 没有真实产品集成 | 模型不能被 API/Scheduler 直接使用 | 高（产品） | 模型层可接受，产品层未完成 |
| 12 | JSON history 不是生产存储 | 并发、迁移、查询能力弱 | 中 | 原型可接受 |
| 13 | passive context 完全不用 | 无法利用睡眠/手机数据 | 低（V1 预期） | 可接受 |
| 14 | 没有 drift 监控 | 用户状态变化后模型可能失准 | 中 | 可接受，V1 可后补 |
| 15 | 没有真实用户测试 reflection 文案 | A–D 四段是否真的能引出有效证据未知 | 中 | 可接受，但建议做访谈 |
| 16 | 没有 baseline 对比 | 无法证明模型比“昨天状态延续”更好 | 高 | 可接受，但 pilot 必须做 |
| 17 | 隐私与审计只做到 quote 级 | 原始 reflection 可能含敏感信息 | 中 | 可接受，但上线前必须处理 |
| 18 | 无心理危机安全策略 | reflection 可能出现自伤/危机表达 | 中 | 需要产品层处理 |

---

## 2. 小优化方案（按优先级）

### P0-1. 真实 LLM 接入 + Evidence Gold Set

**问题：** 现在只验证了 LLM 输出契约，没有验证真实模型的语义准确率。

**小优化：**

- 注入一个真实 `LLMClient`（OpenAI/Anthropic/本地模型均可）。
- 收集 100–200 条真实 reflection，人工标注：
  - evidence_type
  - direction
  - strength
  - evidence_text（逐字）
  - source_field
- 计算每种 evidence 的 precision / recall / F1。
- 加一个 verifier：第二次 LLM 或规则检查，专门判断“quote 是否真的支持这个标签”。
- 对低置信或冲突 evidence 进入人工复核队列。

**预期收益：** 知道 LLM 到底能不能用；把“契约正确”升级为“语义可信”。

**代价/风险：** 需要标注人力；真实 API 有成本；不同模型差异大。

**验收：** quote 审计 100% 通过；关键 evidence（fatigue/stress/self-efficacy）precision 建议 ≥0.85；recall 建议 ≥0.60（具体阈值可按 pilot 调整）。

---

### P0-2. 小规模 Pilot 与 Uncertainty 校准

**问题：** 没有真实 longitudinal 数据；uncertainty 只是工程设定。

**小优化：**

- 20–30 名用户 × 14–28 天，收集 task log + 每晚 reflection。
- 计算：
  - MAE / RMSE（state posterior vs 次日自评或聚合自评）
  - CRPS（概率预测）
  - 50%/80%/95% 区间的实际 coverage
  - prediction error 的均值、方差、自相关
- 用 pilot 数据做离线网格搜索，调 `ρ`、`q`、`κ`、`w_g`。
- 保留 V1 默认值作为 baseline，不直接替换。

**预期收益：** 知道 uncertainty 是过窄还是过宽；知道参数是否离谱。

**代价/风险：** 数据收集周期长；自评本身有偏差；样本小。

**验收：** 80% 区间 coverage 接近 0.8（例如 0.7–0.9）；CRPS 优于 persistence baseline。

---

### P0-3. 隐私脱敏与保留策略

**问题：** `evidence_text` 保存原始 reflection，可能含姓名、地点、健康信息。

**小优化：**

- 发送 LLM 前做 PII 脱敏（姓名、电话、地址、学号）。
- 存储时加密；设置保留期限（例如 90 天）。
- 提供用户删除/导出接口。
- 日志只记录 prompt hash，不记录完整 prompt。
- 明确“不是诊断工具”，遇到危机表达给安全提示与人工资源。

**预期收益：** 降低合规与伦理风险。

**代价/风险：** 脱敏可能损失上下文；需要产品/法务一起定策略。

---

### P1-1. 证据聚类与跨状态折扣

**问题：** “今天压力很大，很累”会同时产生 stress 和 fatigue 两条证据，模型把它们当独立观测，可能双重推高。

**小优化：**

- 给每条 evidence 加一个 `evidence_cluster_id`（同一句/同一段）。
- 同一 cluster 内跨状态证据乘一个折扣（例如 0.8，作为可配置工程参数）。
- 或者限制每个状态每天最多 N 条 evidence。
- 先做敏感性分析：比较折扣 1.0 / 0.8 / 0.6 对 posterior 的影响。

**预期收益：** 减少相关证据的重复计数。

**代价/风险：** 折扣系数也是工程初始化；不要把它包装成论文结论。

**验收：** 同一句同时含 fatigue/stress 时，两个状态的后验移动小于“两条独立证据”的移动；冲突/相关性有记录。

---

### P1-2. 拖延识别的“可选单问”补充

**问题：** 当前只有用户明确说“主动拖延/逃避”才 confirmed，recall 偏低。

**小优化：**

- 当出现“高 start delay + 无明确拖延证据 + 有外部原因线索”时，前端可选择一个**非量表**的单问：
  - “这次延迟更接近：A 外部原因 / B 我自己选择先做别的 / C 说不清”
- 只有 B 才进入 confirmed procrastination；A/C 保持 candidate/unknown。
- 这不是心理量表，只是行为归因；仍然尊重“不要重复问系统已知数据”的原则。

**预期收益：** 提高 recall，同时保持 precision。

**代价/风险：** 增加一次交互；用户可能嫌烦。

**验收：** 外部原因场景 confirmed 仍为 0；主动选择场景 confirmed 提高；用户可跳过。

---

### P1-3. 行为指标缺失偏差

**问题：** `initiation` 的分母是“有日志的任务”，漏记会让开始率偏高；goal attainment 只对有 completion_ratio 的任务取平均。

**小优化：**

- 保留两个口径：
  - conditional rate（有日志任务）
  - coverage（有日志任务 / 计划任务）
- 增加 `missingness_flag`：当天日志覆盖率低于阈值时，降低该指标的 evidence 权重。
- goal attainment 可以加 duration-weighted 版本，避免 5 分钟任务和 2 小时任务等权。
- 不要直接把“无日志”当成 0 完成。

**预期收益：** 指标更诚实，减少“看起来很好”的偏差。

**代价/风险：** 口径变多，前端要解释清楚。

---

### P1-4. 冷启动分层 Warm-up

**问题：** Day 1 固定 0.5/0.25，对高疲劳/低自信用户可能不友好。

**小优化：**

- 前 3–5 天使用更宽的 prior（例如 SD 0.30），并允许个人均值向数据收缩。
- 使用 hierarchical/shrinkage：个人均值 = 群体均值 + 有限权重 × 个人早期均值。
- **仍然不使用 Trait → State 权重**；Trait 只做版本/上下文。
- 如果产品有用户自报的“最近一周平均状态”，可以作为可选 cold-start 输入，但必须标注为自报。

**预期收益：** 更快接近个体水平，同时不伪装成已学习。

**代价/风险：** 早期数据少，收缩权重难定；需要 pilot。

---

### P1-5. 参数敏感性与版本化

**问题：** ρ/q/κ/weights 都是工程值，不知道结论对它们有多敏感。

**小优化：**

- 做 one-at-a-time 敏感性分析：ρ ±0.1、q ±0.05、κ ±0.5、w_g ±0.2。
- 输出 posterior 变化范围，写进 validation artifact。
- 每次改参数升 `config_version`，保留旧 profile 的版本号。
- 不做“自动调参上线”，只做离线分析。

**预期收益：** 知道哪些参数真的重要，避免拍脑袋。

---

### P1-6. 产品集成 Adapter

**问题：** 目前是独立包，不能直接被 DAMN 的 API/Scheduler 使用。

**小优化（属于产品集成，不是模型改动）：**

- 增加 `Task`/`TaskExecution` ORM → DDSR schema 的 mapper。
- 在 Application 层加一个 `DailyStateService`：接收当天 logs + reflection，调用 `DDSREngine`，返回 profile。
- 增加一个只读 endpoint：`GET /users/{id}/dynamic-state?date=...`。
- 把 `next_day_prior` 注入 Scheduler 的 workload/planning 逻辑（先只读，不改变硬规则）。
- 用 Repository 替换 JSON store；保留 JSON store 用于测试。
- 跑全项目测试，确认 Level 1 和现有 150 tests 不受影响。

**预期收益：** 模型真正产生产品价值。

**代价/风险：** 这是本次最大的“未完成部分”，工作量大于模型本身。

---

### P2-1. 日级 → 时段级（可选）

**问题：** 只有日级状态，无法区分上午/下午/晚上。

**小优化：**

- 给 evidence 加可选 `period`（已经有字段），先做 duration-weighted 日聚合。
- 如果产品愿意增加一次 morning check-in，可把 prior 和 posterior 分开：
  - 早上：计划 + 初始 self-efficacy
  - 晚上：执行 + 反思
- 这会增加用户负担；V1 不建议默认开启。

---

### P2-2. Fatigue/Stress 协方差

**问题：** 两个状态独立更新，但现实中 fatigue 和 stress 常一起变化。

**小优化：**

- 先做 post-hoc 相关性监控，不改模型。
- 如果 pilot 显示强相关，再考虑：
  - 共享 cause discount（P1-1）
  - 或二元 Gaussian copula / 多元先验
- 不要在没有数据前加复杂协方差结构。

---

### P2-3. Passive Context 的“只读睡眠”版本

**问题：** 目前完全不用 passive context。

**小优化：**

- 保持 `null` 为默认。
- 如果未来接入手环，只把 `sleep_duration` / `sleep_quality` 作为 fatigue prior 的协变量，且系数明确标注为工程初始化。
- **不要把 screen time / unlock count 直接映射成拖延、低自律或疲劳。**
- 先做用户授权与隐私设计。

---

### P2-4. Drift 监控

**问题：** 用户状态可能随时间变化，模型没有监控。

**小优化：**

- 监控每日 prediction error 的 EWMA。
- 如果连续 N 天 |standardized error| 超过阈值，标记“模型可能失准”，提示重新校准或增加 reflection 引导。
- 不做在线学习，只做告警。

---

## 3. 建议的实验设计（不需要写代码）

### 3.1 Evidence Gold Set

- 样本：100–200 条真实 nightly reflection。
- 标注：2 名标注者独立标 evidence_type / direction / strength / quote；分歧由第三人裁决。
- 指标：per-type precision / recall / F1；quote 审计通过率；误报类型分布。
- 目的：验证 LLM 是否真的能替代 rule-based fallback。

### 3.2 Pilot

- 样本：20–30 名用户 × 14–28 天。
- 数据：TaskPlan / TaskExecution / 四段 reflection / 可选 passive context。
- 指标：
  - state MAE / RMSE
  - CRPS
  - 50/80/95% interval coverage
  - prediction error 自相关
  - 用户对反思问题的理解度（5–10 人访谈）
- Baseline：
  - mean-only（永远 0.5）
  - persistence-only（昨天状态）
  - rule-based extractor
  - LLM extractor
- 目的：证明“比简单 baseline 更好”，而不是只证明“能跑”。

### 3.3 Ablation

- 去掉 reflection，只用 task log。
- 去掉 goal attainment，只用 reflection。
- 加/不加 evidence cluster discount。
- 不同 ρ/q/κ。
- 目的：知道每个组件是否真的有用。

---

## 4. 最终建议

**V1 不要继续加模型复杂度。**  
当前最值得投入的是：

1. 真实 LLM + gold set；
2. 小规模 pilot + uncertainty 校准；
3. 证据聚类折扣；
4. 产品 adapter / API / Scheduler 集成；
5. 隐私与安全策略。

这五件事做完，再考虑是否进入 V2 的个性化 transition learning、时段级状态、passive context 和 fatigue/stress 协方差。
