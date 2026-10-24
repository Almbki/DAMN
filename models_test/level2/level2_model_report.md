# DDSR-V1 Level 2 交付说明（中文版）

**模型：** `DDSR-V1` / `ddsr_v1`  
**Schema：** `1.0`  
**Config：** `ddsr_v1_config_1`  
**验证结果：** 54 个测试全部通过；13 项机器检查全部为 true  
**最终标记：** `DYNAMIC_STATE_MODEL_V1_READY = YES`

> 这个 YES 的含义是：**模型边界、schema、两阶段更新、审计要求和测试机制满足 V1 要求**。  
> 它不代表已经在真实长期数据上验证了预测准确率。

---

## 1. 交付物

```text
models_test/level2/
├── ddsr/                         # DDSR-V1 核心实现
│   ├── schemas.py                # TaskPlan / TaskExecution / Reflection / Evidence / Profile
│   ├── config.py / config.json   # 全部可调参数与来源
│   ├── trait_context.py          # Level 1 TraitProfile 只读适配
│   ├── task_metrics.py           # 自动 TaskLog 派生指标
│   ├── state_model.py            # Stage 1 prediction + Stage 2 correction
│   ├── engine.py                 # 每日流程编排
│   ├── store.py                  # JSON 长期历史
│   └── evidence/
│       ├── base.py               # EvidenceExtractor 接口 + quote 审计
│       ├── llm.py                # LLM 证据抽取器 + LLMClient 接口
│       └── rule_based.py         # 离线确定性 fallback
├── tests/                        # 54 个 pytest
├── run_validation.py             # 生成机器可读验证结果
├── level2_validation.json        # 机器可读验证 artifact
├── level2_model_report.md        # 本文件
└── level2_optimization_recommendations.md
```

运行方式：

```bash
cd models_test/level2
uv run --project ../.. --extra dev python -m pytest tests -rA
uv run --project ../.. --extra dev python run_validation.py
```

---

## 2. 与你原来给的架构相比，差异在哪里

这是本次交付最需要说清楚的部分。

| 维度 | 你原来的项目/任务架构 | 本次实现 | 差异与影响 |
|---|---|---|---|
| 代码位置 | DAMN 的 `app/` 分层：API → Application → Domain/Core → Infrastructure | 独立的 `models_test/level2/ddsr/` Python 包 | **模型逻辑独立可测，但尚未接入 `app/api`、`app/application/services`、Repository、Alembic** |
| Level 1 接入 | TraitProfile V1 是上层模型输出 | `TraitContext.from_profile(dict)` 只读解析 N/E/O/A/C 的 theta/se 和版本 | 没有 import `cat.py`，没有改 GRM/CAT；theta 不参与状态计算（测试验证） |
| 任务数据 | 项目已有 ORM/domain `Task`、`TaskExecution`，字段更多（`scheduled_date`、`start_time`、`status`、`cognitive_load` 等） | 使用最小 Pydantic `TaskPlan` / `TaskExecution` | 需要一个 adapter 把项目 ORM 映射到 DDSR schema；目前没有写这个 adapter |
| LLM 调用 | “通用 LLM + constrained structured output” | 实现 `LLMEvidenceExtractor` + `LLMClient` 接口 + 严格 JSON/Pydantic/quote 审计 | **没有绑定真实 provider/API key**；生产时需要注入一个 `LLMClient`（OpenAI/Anthropic/本地模型均可） |
| 证据抽取 fallback | 任务没有要求 | 额外实现了 `RuleBasedEvidenceExtractor` | 用于测试、离线 replay、LLM 不可用时降级；不是生产主路径 |
| 夜间反思 | 四段引导式文字/语音输入 | `ReflectionInput` 四字段 + `input_modality` | 数据接口支持；**没有实现前端 UI、定时任务、语音转文字** |
| 状态模型 | 两阶段 DDSR，V1 要简单、参数少 | AR(1) 先验 + 0–1 网格 Bayes 校正 | 满足“简单、可解释、不虚构系数”；没有深度时序网络 |
| 行为指标 | 四类：initiation / persistence / goal_attainment / procrastination_evidence | 已实现，且与状态严格分离 | 具体公式是工程定义；原架构没有给出精确公式 |
| 拖延判断 | 不能仅由 start delay 判断 | 只有用户明确描述“主动拖延/逃避”才 confirmed；late start 只是 candidate | 外部打断、生病、计划变化、任务难度被 schema 拒绝为拖延 |
| Passive context | 预留接口，V1 不采集真实手机数据 | 统一 `PassiveContext`，默认 `null`，V1 完全不解释 | 符合 V1；screen time 不会被当成拖延/疲劳 |
| 持久化 | 项目用 SQLAlchemy + Alembic | `JsonHistoryStore` 保存每日 profile | 适合模型验证/原型；**不是生产数据库方案**，没有迁移 |
| 调度器 | Scheduler 可以使用 prior | 输出 `next_day_prior`，但**没有注入现有 Scheduler/PlanService** | 模型输出已准备好，集成还没做 |
| 个性化 | V1 不要求可靠个性化学习 | `personalization_enabled = false`，只保存 prediction error | 没有声称已实现个性化；prediction error 是未来数据资产 |
| 测试范围 | 项目有 150 个测试 | 独立的 54 个 Level 2 测试 | **没有跑全项目 150 个测试**，因为没有改 `app/` 代码；Level 1 文件也未修改 |
| 量表 | 论文使用 1–5 / 1–9 / 1–6 | 统一 0–1 工程尺度 | 不能直接套用论文系数；报告里明确标注为工程初始化 |

### 一句话总结差异

> **模型层已经实现并验证；产品层（API、数据库、调度器、前端、真实 LLM、语音转写）还没有接入。**  
> 这不是模型逻辑缺失，而是本次交付刻意把 Level 2 做成一个独立、可测试、可替换的包，避免动 Level 1 和现有 `app/` 架构。

---

## 3. 科学依据

| 资产 | 在 DDSR-V1 中支持什么 | 明确没有拿走什么 |
|---|---|---|
| Bellhäuser, Dignath & Theobald (2023) | 36 天 morning/evening diary；daily self-efficacy、planning、adherence、procrastination、effort；within-person variance 很大（ICC 17–47%） | 没有照抄 6 点量表、反馈句、multilevel 系数 |
| Wäschle, Allgaier, Lachner et al. (2014) | self-efficacy ↔ perceived goal achievement 的 reciprocal 正向关系；procrastination ↔ goal achievement；self-efficacy 中介 | 这是 **19 周、每周** 的研究，不是日级；没有把周级系数搬到日级 |
| Kahneman, Krueger, Schkade, Schwarz & Stone (2004), DRM | 晚上系统性重构当天 episode；比单次全局自评负担低、回顾偏差小 | 没有实现完整 DRM 量表、episode 编码、affect 维度 |
| Åkerstedt et al. (2014) | fatigue/stress 是合理的日级状态；42 天 diary；fatigue 4 项 α=.83；stress 1–9；日级 stress–fatigue 关联（单变量 β≈.108，多变量 β≈.035） | 没有把回归系数当成 DDSR 转移系数；V1 不实现睡眠/actigraphy |
| Loeffler, Stumpp, Grund et al. (2019) | 每日 electronic diary：早上计划学习时间；晚上拖延、实际/有效学习时间、计划工作量完成度；10 类拖延原因；**行为延迟本身不能判定拖延** | 没有实现干预教程、模块匹配、真实手机采集 |

**核心科学 caution：** 这些论文没有给出一个可直接用于“三状态日级转移”的已验证系数。因此 DDSR-V1 只继承构念和方向，不继承数值系数。

---

## 4. 状态与行为边界

### 4.1 三个 Daily Dynamic States

统一使用 **0–1 工程尺度**（不是论文原始量表，也不是临床量表）：

| 状态 | 高值含义 |
|---|---|
| `fatigue` | 更疲劳 |
| `stress` | 压力更大 |
| `self_efficacy` | 更有信心应对今天/明天 |

每个状态保存：

- `value`：后验均值
- `uncertainty`：后验标准差
- `observed_on`：日期
- `prior` / `prior_uncertainty`
- `evidence_availability`：`none` / `reflection_only` / `task_log_only` / `reflection_and_task_log`
- `evidence_count`
- `conflict`

### 4.2 四类行为指标（与状态严格分离）

- `initiation`：开始率、准时数、平均 start delay、日志覆盖率
- `persistence`：duration ratio、continuation rate、interruption count
- `goal_attainment`：已记录任务的平均 completion ratio
- `procrastination_evidence`：confirmed 证据 + late-start candidates

**关键边界：**

- late start 只是 candidate，不是 procrastination。
- 只有用户明确说“我主动拖延/逃避”才 confirmed。
- 外部打断、生病、任务难度、计划变化被 schema 直接拒绝为 procrastination。
- 行为指标不会自动变成“自律分数”或人格判断。

---

## 5. 输入与输出

### 输入

1. **TraitProfile V1（只读）**：N/E/O/A/C 的 theta/se + model/version。
2. **TaskPlan**：`task_id`、`planned_start`、`estimated_duration_minutes`、`deadline`、`difficulty`。
3. **TaskExecution**：`actual_start`、`actual_duration_minutes`、`completion_ratio`、`completed`、`interruption_count`。
4. **ReflectionInput**：四段可选文字/语音转写：
   - A `day_review`：今天做得怎么样？
   - B `stuck_points`：哪里卡住了？
   - C `state_review`：今天状态怎么样？
   - D `tomorrow_outlook`：明天怎么看？
5. **PassiveContext（可选，默认 null）**：预留接口，V1 不解释。

### 输出：DynamicStateProfile V1

- model/schema/config 版本、日期、cold start、gap days
- source Trait model 版本元数据
- `fatigue` / `stress` / `self_efficacy`
- `prior` / `current_posterior`
- `prediction_error`（raw + standardized）
- `next_day_prior`（value + uncertainty + source）
- `behavioral_indicators`
- `evidence` 元数据
- `passive_context_used = false`

---

## 6. 两阶段更新方程

### Stage 1 — Prediction

\[
\mu_{d,j}^{-}=\rho_j\mu_{d-1,j}^{+}+(1-\rho_j)\mu_j^{pop}
\]

\[
(\sigma_{d,j}^{-})^2=\rho_j^2(\sigma_{d-1,j}^{+})^2+q_j^2
\]

Day 1 cold start：

\[
\mu_{1,j}^{-}=0.5,\qquad \sigma_{1,j}^{-}=0.25
\]

这是透明的 population/neutral prior，不是个体化估计。

### Stage 2 — Correction

在 0–1 的 101 点网格上：

\[
p_j(x\mid e)\propto \mathcal N(x;\mu_{d,j}^{-},(\sigma_{d,j}^{-})^2)\prod_e L_{j,e}(x)
\]

状态证据：

\[
L_{j,e}(x)=\exp(\kappa s_e\delta_e(x-0.5))
\]

Goal attainment 只更新 self-efficacy：

\[
L_{SE,g}(x)=\exp(\kappa w_g(g_d-0.5)(x-0.5))
\]

Procrastination / interruption 不进入状态似然，只作为行为证据。

### Prediction error 与明日 prior

\[
e_{d,j}=\mu_{d,j}^{+}-\mu_{d,j}^{-},\qquad z_{d,j}=e_{d,j}/\sigma_{d,j}^{-}
\]

\[
\mu_{d+1,j}^{-}=\rho_j\mu_{d,j}^{+}+(1-\rho_j)\mu_j^{pop}
\]

`next_day_prior` 保存 value + uncertainty；次日直接使用它（已测试一致）。

---

## 7. 参数与来源

参数集中在 `ddsr/config.json`；每项都有 `category` 和 `note`。

| 参数 | 默认值 | 类别 |
|---|---:|---|
| 状态尺度 | 0–1 | engineering initialization |
| 状态集合 | fatigue / stress / self_efficacy | literature-supported design choice |
| cold start mean | 0.5 / 0.5 / 0.5 | engineering initialization |
| cold start SD | 0.25 | engineering initialization |
| persistence ρ | 0.6 / 0.6 / 0.6 | engineering initialization（AR 设计有文献一致性，数值非论文估计） |
| process noise q | 0.12 / 0.12 / 0.12 | engineering initialization |
| evidence sharpness κ | 2.0 | engineering initialization |
| strength weights | weak .35 / moderate .65 / strong 1.0 | engineering initialization |
| goal attainment weight | 0.6 | engineering initialization（方向来自 Wäschle） |
| uncertainty floor / ceiling | 0.02 / 0.50 | engineering initialization |
| grid | 0–1, 101 点 | engineering initialization |
| late-start candidate | 60 分钟 | engineering initialization（仅 candidate） |
| min quote chars | 2 | engineering initialization |
| conflict policy | symmetric Bayes product | engineering initialization |
| extraction failure policy | fail-closed | engineering initialization |
| passive context | disabled | engineering initialization |
| personalization | disabled | learned/personalized（V1 为空） |

**V1 没有任何参数声称是已学习或已个体化的。**

---

## 8. LLM 证据提取：怎么做的、没有 API 怎么测的

### 8.1 设计

`LLMEvidenceExtractor` 不直接依赖某个厂商 SDK，而是依赖一个很小的接口：

```python
class LLMClient(Protocol):
    def complete(self, prompt: str) -> str: ...
```

生产时注入真实客户端；测试时注入 `StaticLLMClient(response)`，它只是返回固定字符串，并记录 prompt。

LLM 只能返回：

```text
ExtractionResult
└── evidence: [
      EvidenceItem
      ├── evidence_type: fatigue | stress | self_efficacy | procrastination | interruption
      ├── direction: increase | decrease
      ├── strength: weak | moderate | strong
      ├── period: morning | afternoon | evening | night | unspecified
      ├── task_id: 可选，必须是已知任务
      ├── cause_category: 可选
      ├── voluntary: 可选
      ├── evidence_text: 必须是 reflection 的逐字子串
      └── source_field: day_review | stuck_points | state_review | tomorrow_outlook
    ]
```

`ExtractionResult` 和 `EvidenceItem` 都是 `extra="forbid"`。因此 LLM 不可能偷偷返回 `state_value`、`prediction`、`diagnosis` 之类的字段。

### 8.2 没有 API 时实际跑了哪些测试

测试使用的是**固定的假 LLM 响应**，不是真实模型：

| 测试 | 输入 | 预期结果 |
|---|---|---|
| 合法 JSON | `{"evidence":[...]}`，quote 与原文一致 | 成功得到 1 个 `EvidenceItem` |
| 非法 JSON | `not json` | 抛 `EvidenceExtractionError` |
| Markdown 代码围栏 | ```json ... ``` | 拒绝（只接受裸 JSON） |
| Schema 不合法 | 缺少必填字段 | 拒绝 |
| 偷偷加状态值 | 多一个 `state_value: 0.9` | 拒绝（`extra="forbid"`） |
| 编造 quote | 原文是“今天很累”，quote 写“我很累” | 拒绝（quote 必须是原文子串） |
| 编造 task_id | `task_id="unknown"` | 拒绝（必须是已知任务） |
| 外部原因伪装成拖延 | `procrastination` + `external_interruption` | 拒绝（语义 guard） |

### 8.3 这说明什么、不说明什么

**说明：**

- 抽取器的输入输出契约是可靠的。
- 非法输出不会污染状态。
- 证据必须可审计（逐字 quote）。
- 引擎在抽取失败时 fail-closed，不会乱猜。

**不说明：**

- 没有验证某个真实 LLM 的语义准确率。
- 没有真实 API 调用。
- 没有测量真实 reflection 上的 precision/recall。

真实上线前需要：接入 `LLMClient`，准备 100–200 条人工标注 reflection，测每种 evidence 的 precision/recall，并加第二道 verifier。

---

## 9. 冷启动与历史

- **Day 1**：0.5 / 0.25 中性 prior；`cold_start = true`；prediction error 仍然计算。
- **Day 2+**：使用上一天保存的 `next_day_prior`。
- **日期缺口**：按 gap days 重复 transition；`gap_days` 保存。
- **历史**：`JsonHistoryStore` 追加每日 profile；prediction error 保留。
- **不伪装个性化**：V1 不学习 transition 参数。

---

## 10. 测试与验证结果

**命令：**

```bash
python -m pytest tests -rA
```

**结果：**

```text
54 passed, 0 failed
```

**13 项机器检查全部 true：**

- states 全部在 0–1
- uncertainty 有界
- prediction error 保存且算术正确
- next-day prior 与次日 prior 一致
- 10 日 replay 无数值爆炸、无状态锁死
- 外部打断 + 高 start delay 不产生 confirmed procrastination
- 缺失 task log 不被当作失败
- 无证据时 posterior 保持 prior
- Level 1 只读契约通过
- replay 确定性
- passive context 被忽略
- LLM 只接受通过 quote/schema 审计的证据
- 参数来源完整，personalization 关闭

**Synthetic replay：**

| 场景 | 结果 |
|---|---|
| 高完成 + 低疲劳 | fatigue/stress 低于 prior，self-efficacy 高于 prior |
| 高 start delay + 外部事件 | confirmed procrastination = 0，candidate = 1，interruption evidence 存在，状态不变 |
| 高 start delay + 明确主动逃避 | confirmed procrastination = 1，`voluntary=True`，avoidance |
| 高疲劳 + 低完成 | fatigue/stress 高于 prior，self-efficacy 低于 prior |
| 当日失败但明日高 self-efficacy | self-efficacy 高于 prior，tomorrow_outlook 证据保留 |
| 无 reflection，仅 task log | fatigue/stress 不变，self-efficacy 由 goal attainment 更新 |
| 10 日 replay | 全部有界，fatigue 有变化，无锁死 |

---

## 11. 当前限制

1. 没有大规模真实 longitudinal ground truth，**不声称预测准确率**。
2. 0–1 是工程尺度，不是论文量表或临床量表。
3. ρ、q、κ、strength weights、goal-attainment weight 都是工程初始化。
4. Wäschle 是每周研究，只继承方向，不继承周级系数。
5. Åkerstedt 的日级回归系数没有搬进状态转移。
6. Rule-based fallback 召回有限；生产路径是 LLM，但尚未接真实 API。
7. Passive context 接口存在，但 V1 完全不解释。
8. 缺失 task log 不会被当作 0 完成；initiation rate 以有日志任务为条件。
9. 拖延识别故意保守，依赖用户明确措辞。
10. 不是诊断工具或心理健康量表。
11. V1 不学习个性化转移参数，只保存 prediction error。
12. 未接入 DAMN 的 API/Service/Repository/Scheduler；未跑全项目 150 tests。

更细的缺陷与优化建议见：`level2_optimization_recommendations.md`。

---

## 12. 结论

```text
DYNAMIC_STATE_MODEL_V1_READY = YES
```

这个 YES 是 **模型层/契约层** 的就绪标记，不是真实数据上的精度声明。  
下一步最有价值的工作不是继续加模型复杂度，而是：接真实 LLM、做小规模 pilot、校准 uncertainty、补产品集成。
