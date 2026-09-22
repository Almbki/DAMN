你现在需要为一个正在实际开发、并准备参加比赛的 **AI 自适应任务规划系统**进行前期研究和论文资料检索。

我们的系统核心不是传统 Todo List，而是一个根据**用户目标、理论任务工作量、用户历史执行情况、当前状态和反馈**持续调整计划的闭环系统。

例如，用户要求在 DDL 前学完高等数学。单纯的 LLM 很容易给出“今天学习高数 45 分钟”，但实际上不同章节的理论工作量不同，而且不同用户的学习速度、基础、精力和任务完成能力也不同。因此我们需要研究：

> **如何获得关于任务、学习、精力、压力、拖延、认知负荷、目标完成和反馈调节的可靠理论依据，并将这些研究结果转化为规则、用户状态、统计模型、预测模型或 LLM Harness，从而让 LLM 的规划更加准确、稳定和个性化。**

这里**不要预设必须使用机器学习**。

如果某个问题用规则、统计方法、简单用户模型就可以解决，就不需要为了使用 ML 而使用 ML。模型/算法可以作为 LLM 的辅助，例如：

* 在简单情况下替代 LLM，减少 LLM 调用；
* 根据用户历史数据给 LLM 提供更加准确的上下文；
* 对 LLM 生成的计划进行独立验证；
* 判断什么时候需要调用 LLM 进行复杂重规划；
* 对任务耗时、完成概率、压力等进行预测；
* 为 LLM 提供结构化的用户状态。

因此，研究的最终目的不是“找论文做机器学习”，而是建立：

```text
研究结论
↓
可观测变量
↓
用户状态 / 任务状态
↓
Rule / Statistical Model / ML / LLM Harness
↓
更可靠的任务规划
```

# 执行约束（强制）

1. **调研必须真实执行**：严禁未实际搜索/阅读就凭记忆输出论文条目（此前会话出现过幻觉输出）。每条文献必须来自实际检索结果，源链接必须可访问。
2. **数量下限**：每个研究方向（共 11 个）实际检索并阅读的文献不少于 **20 篇**；最终采纳多少不做硬性要求，但须在输出中注明"检索 N 篇，采纳 M 篇"。
3. **资料落盘位置**：如需下载 PDF / 保存网页快照等阅读材料，统一保存在本仓库 `doc/` 目录下新建的子文件夹中（如 `doc/research/<方向编号>-<方向名>/`），**禁止**放到 `%temp%` 等系统临时目录。
4. 每个方向的输出文件也放在对应子文件夹中，最终汇总映射文档放在 `doc/` 根下。

# 每篇论文必须提取的信息

不要只返回标题和摘要。搜索到的文献给出清单，格式：前半部分，按照国内论文引用格式；中间后半部分，按前文顺序给出源链接。

每篇论文至少整理：

```text
国内论文引用格式：

源链接：

研究问题：

核心理论：

Independent Variables：

Dependent Variables：

主要结论：

结论的证据强度：

研究局限：

与本项目的关系：

可以支持什么系统设计：

可以采集什么数据：

可以形成什么 User State：

可以作为 Rule / Statistical Model / ML / LLM Harness 的哪一部分：

推荐优先级及原因：
```

# 信息搜索的筛选原则

不要只寻找“看起来相关”的论文。

每篇资料需要判断：

### A. 是否有可靠的理论/实验依据？

优先：

* peer-reviewed paper
* systematic review
* meta-analysis
* 高质量会议论文
* 高质量实验研究

---

### B. 变量是否可以被我们的系统观察？

优先关注：

```text
Task Logs
Completion Time
Task Success
Self-report
Daily Diary
Experience Sampling
Behavioral Data
Historical Performance
Smartphone Data
```

如果论文依赖：

```text
EEG
fMRI
实验室设备
复杂生理传感器
```

可以保留理论价值，但需要明确标记。

---

### C. 这个研究结果应该如何进入系统？

每篇论文必须尝试判断：

```text
Rule
Statistical Model
User Model
ML
LLM Context
LLM Harness
RAG
Evaluation
```

不要默认全部变成 ML。
---

# 最终产出：Research → System Mapping

最终不要只给出一堆论文。

需要形成类似下面的映射：

| 研究发现         | 系统变量                   | 可能实现               |
| ------------ | ---------------------- | ------------------ |
| 认知负荷影响表现     | cognitive_load         | Rule / User Model  |
| 个体任务耗时差异     | duration_factor        | Statistical / ML   |
| 压力影响完成率      | stress                 | User Model         |
| 时间段影响表现      | time_slot              | Predictor          |
| 子目标有助于执行     | task_granularity       | Task Decomposition |
| 反馈能够改善规划     | feedback               | Replanning         |
| LLM 需要外部验证   | plan_validation        | Harness            |
| 简单任务无需 LLM   | routing                | LLM Router         |
| 历史执行能够预测未来表现 | historical_performance | User Model         |

最终需要回答四个问题：

> **1. 哪些科学规律应该固化成规则？**

> **2. 哪些应该进入用户状态模型？**

> **3. 哪些值得建立统计/机器学习模型？**

> **4. 哪些应该交给 LLM，以及什么情况下根本不应该调用 LLM？**

研究的最终目的，是帮助我们建立一个：

```text
Scientific Evidence
        ↓
User / Task State
        ↓
Rule / Model / Knowledge
        ↓
LLM Harness
        ↓
Planning
        ↓
Execution
        ↓
Feedback
        ↓
Updated State
```

的可靠闭环，而不是单纯收集“如何提高效率”的论文。




---

# 1. 精力 / Energy / Fatigue

### 推荐关键词

英文：

* mental energy
* subjective energy
* cognitive fatigue
* mental fatigue
* perceived fatigue
* fatigue and task performance
* energy level and performance
* fatigue and productivity
* fatigue and learning
* time of day cognitive performance

中文：

* 精力
* 主观精力
* 精神疲劳
* 认知疲劳
* 心理疲劳
* 疲劳与任务表现
* 精力与学习效率
* 精力与生产力

### 重点研究

1. 精力/疲劳是否能够预测任务完成效率？
2. 精力是否与任务完成时间存在关系？
3. 疲劳是否会影响任务完成概率？
4. 高认知任务是否更加依赖较高的精力状态？
5. 精力是否存在时间段上的规律？
6. 用户自评精力是否具有足够的预测价值？

### 可转化为 Feature

```text
energy_level
fatigue_level
time_of_day
sleep_duration
sleep_quality
recent_high_cognitive_minutes
recent_task_load
```

### 可能支持的系统模块

```text
User State
Task Duration Predictor
Completion Predictor
Time Slot Recommendation
Task Load Adjustment
LLM Context
```

---

# 2. 拖延 / Procrastination

### 推荐关键词

英文：

* procrastination
* academic procrastination
* task delay
* procrastination and task difficulty
* procrastination and self-regulation
* procrastination and goal pursuit
* temporal motivation theory
* procrastination and deadline
* procrastination and task aversion

中文：

* 拖延
* 学业拖延
* 任务拖延
* 自我调节
* 时间动机理论
* 任务难度与拖延
* 截止日期与拖延

### 重点研究

1. 什么因素能够预测用户是否会推迟开始任务？
2. 什么因素能够预测任务最终是否完成？
3. 任务难度是否影响拖延？
4. 截止日期距离如何影响任务执行？
5. 任务价值、即时奖励、任务厌恶是否影响执行？
6. 历史拖延行为能否预测未来拖延？

特别关注：

* task difficulty
* task value
* deadline distance
* task aversion
* self-efficacy
* perceived cost
* historical delay

### 可转化为 Feature

```text
task_difficulty
task_value
deadline_distance
task_aversion
self_efficacy
historical_delay
historical_completion_rate
```

### 可能支持的系统模块

```text
Completion Predictor
Task Prioritization
Task Granularity
Replanning Trigger
LLM Harness
```

---

# 3. 任务拆解 / Task Decomposition

### 推荐关键词

英文：

* task decomposition
* goal decomposition
* hierarchical task planning
* goal hierarchy
* subgoal
* task granularity
* task chunking
* goal setting
* subgoal setting
* implementation intention

中文：

* 任务拆解
* 目标拆解
* 层级任务规划
* 子目标
* 任务粒度
* 任务分块
* 目标设定

### 重点研究

1. 长期目标拆解成多大的任务粒度更适合执行？
2. 子目标是否能够提高目标完成率？
3. 任务过大是否增加拖延？
4. 任务过细是否增加管理成本？
5. 如何判断一个任务是否应该继续拆解？
6. 不同任务类型是否需要不同的拆解粒度？

例如：

```text
学习高数
```

究竟应该拆成：

```text
第一章极限
```

还是：

```text
观看第1节视频
完成例题
完成基础练习
总结
```

### 可转化为 Feature

```text
task_depth
task_size
subtask_count
estimated_duration
task_complexity
completion_criteria_count
```

### 可能支持的系统模块

```text
Goal Decomposition Agent
Task Generator
Task Granularity Controller
LLM Harness
```

---

# 4. 任务耗时 / Task Duration / Human Performance

### 推荐关键词

英文：

* task completion time prediction
* task duration prediction
* time-on-task
* human performance prediction
* individual productivity
* task performance modeling
* completion time prediction
* learning time prediction
* individual differences in task performance

中文：

* 任务完成时间
* 任务耗时预测
* 学习时间预测
* 人类表现预测
* 个体差异
* 任务表现建模

### 重点研究

1. 什么因素能够预测一个任务实际需要多少时间？
2. 理论任务时间与实际完成时间之间存在什么关系？
3. 用户历史执行时间能否用于预测未来任务？
4. 任务难度、用户能力、任务类型如何共同影响耗时？
5. 是否可以建立用户自己的“任务耗时倍率”？
6. 简单统计模型是否已经足够，还是需要 ML？

这是本项目非常重要的研究方向。

例如：

```text
理论时间 = 60 min

用户历史：
同类任务平均 = 92 min

当前状态：
疲劳较高

最终：
预测约 110 min
```

### 可转化为 Feature

```text
theoretical_duration
historical_duration
task_type
task_difficulty
user_skill
task_size
time_of_day
fatigue
cognitive_load
```

### Target

```text
actual_duration
```

### 可能支持的系统模块

```text
Duration Predictor
User Model
Scheduler
LLM Context
LLM Verification
```

---

# 5. 认知负荷 / Cognitive Load

### 推荐关键词

英文：

* cognitive load
* cognitive workload
* mental workload
* intrinsic cognitive load
* task complexity and cognitive load
* cognitive load and performance
* workload and task performance

中文：

* 认知负荷
* 认知工作负荷
* 心理负荷
* 心智负荷
* 任务复杂度与认知负荷
* 认知负荷与任务表现

### 重点研究

1. 任务复杂度如何影响认知负荷？
2. 认知负荷是否影响任务完成时间？
3. 认知负荷是否影响任务完成概率？
4. 高认知任务连续出现是否影响后续任务表现？
5. 一天能够安排多少高认知任务？
6. 是否存在适合个体化的认知负荷上限？

我们的系统已经存在类似经验规则：

```text
高认知任务不能连续
数学和算法尽量不同天
每日任务量存在上限
任务之间存在缓冲
```

需要通过研究判断：

> 哪些规则有理论依据，哪些只是经验规则，哪些应该进一步通过用户数据个性化。

### 可转化为 Feature

```text
cognitive_load
task_complexity
high_cognitive_minutes
consecutive_high_load_tasks
daily_load
```

### 可能支持的系统模块

```text
Rule Engine
User State
Load Predictor
Scheduler
Plan Validator
```

---

# 6. 压力与目标完成 / Stress & Goal Attainment

### 推荐关键词

英文：

* stress and task performance
* perceived stress
* workload and performance
* stress and productivity
* stress and procrastination
* stress and goal attainment
* workload management
* deadline pressure
* pressure and performance

中文：

* 压力
* 感知压力
* 心理压力
* 工作负荷
* 压力与任务完成
* 压力与拖延
* 截止日期压力
* 压力与表现

### 重点研究

1. 压力与任务完成之间是什么关系？
2. Deadline pressure 是否影响执行？
3. 高压力是否一定提高执行效率？
4. 压力是否存在非线性影响？
5. 压力是否会导致拖延、任务回避或任务完成率下降？
6. 用户自评压力是否能够预测后续表现？

需要特别注意：

不要预先假设“适度压力最好”一定成立。

需要根据论文中的实验结果判断。

### 可转化为 Feature

```text
stress_level
deadline_pressure
perceived_workload
recent_failure_count
deadline_distance
daily_task_load
```

### 可能支持的系统模块

```text
Stress Model
Completion Predictor
Load Adjustment
Replanning
LLM Context
```

---

# 7. 时间段 / Circadian Rhythm / Time of Day

### 推荐关键词

英文：

* time of day and cognitive performance
* circadian rhythm and cognition
* chronotype and productivity
* chronotype and academic performance
* time of day task performance
* chronotype and learning

中文：

* 时间段与认知表现
* 生理节律
* 昼夜节律
* 时间类型
* 高效时间
* 时间段与学习效率

### 重点研究

1. 时间段是否影响认知表现？
2. 不同类型任务是否适合不同时间段？
3. 个体之间是否存在明显差异？
4. 用户是否存在稳定的个人高效时间段？
5. 历史行为能否预测个人最佳任务时间？

### 可转化为 Feature

```text
time_of_day
day_of_week
chronotype
task_type
historical_performance_by_time
```

### 可能支持的系统模块

```text
Time Slot Predictor
Scheduler
User Model
```

---

# 8. 学习、记忆与复习 / Memory & Learning

### 推荐关键词

英文：

* forgetting curve
* memory retention
* spaced repetition
* spacing effect
* retrieval practice
* learning retention
* individual differences in memory
* adaptive learning

中文：

* 遗忘曲线
* 记忆保持
* 间隔重复
* 间隔效应
* 检索练习
* 学习保持
* 自适应学习

### 重点研究

1. 学习内容随时间如何遗忘？
2. 间隔重复和检索练习是否能够改善保持？
3. 复习时间如何确定？
4. 不同用户的遗忘速度是否存在差异？
5. 用户实际练习表现能否用于个性化复习？

### 可转化为 Feature

```text
knowledge_mastery
last_review_time
review_count
retrieval_accuracy
task_difficulty
time_since_learning
```

### 可能支持的系统模块

```text
Review Scheduler
User Model
Learning Planner
```

---

# 9. 反馈调节 / Feedback Regulation / Adaptive Planning

### 推荐关键词

英文：

* adaptive planning
* adaptive scheduling
* feedback-driven planning
* personalized planning
* personalized scheduling
* closed-loop planning
* feedback control
* human-in-the-loop
* adaptive goal setting
* adaptive learning
* personalized intervention

中文：

* 反馈调节
* 自适应规划
* 动态调度
* 个性化规划
* 闭环控制
* 人在回路
* 自适应学习
* 个性化干预

### 重点研究

我们系统的核心闭环是：

```text
Plan
 ↓
Execution
 ↓
Feedback
 ↓
State Estimation
 ↓
Adjustment
 ↓
New Plan
```

重点寻找：

1. 如何根据执行反馈调整下一阶段计划？
2. 什么时候应该重新规划？
3. 反馈频率应该多高？
4. 如何避免频繁调整导致系统震荡？
5. 如何判断用户是“任务太难”还是“执行状态异常”？
6. 如何在保持长期目标的同时动态改变短期任务？

### 可转化为 Feature

```text
completion_rate
planned_vs_actual_duration
failure_count
feedback_frequency
plan_change_frequency
goal_progress
```

### 可能支持的系统模块

```text
Replanning
User Model Update
Scheduler
LLM Harness
```

---

# 10. LLM 规划与 Harness / LLM Planning & Reliability

### 推荐关键词

英文：

* LLM planning
* LLM task planning
* LLM agent planning
* LLM planning reliability
* LLM hallucination mitigation
* LLM verifier
* LLM critique
* LLM tool use
* LLM planning with constraints
* LLM agents with external memory
* LLM agent evaluation
* LLM workflow orchestration
* LLM routing
* LLM cost optimization
* model routing
* adaptive LLM invocation
* LLM cascade

中文：

* 大语言模型规划
* LLM Agent 规划
* LLM 可靠性
* LLM 验证器
* LLM 工具调用
* LLM 约束规划
* LLM 路由
* LLM 成本优化
* Agent 规划
* Agent 评估

### 重点研究

这里不要只搜索“LLM 如何规划任务”。

我们尤其关心：

### 1. 什么时候不应该调用 LLM？

例如：

```text
简单每日微调
↓
Rule + Scheduler
```

而：

```text
目标发生重大变化
严重偏离
复杂任务拆解
用户主动要求重新规划
↓
LLM
```

寻找：

> LLM routing / model routing / adaptive invocation / cascaded models 等相关研究。

---

### 2. 如何用外部模型辅助 LLM？

例如：

```text
LLM
 +
Duration Predictor
 +
User State
 +
Rule Engine
```

寻找：

> Tool-augmented LLM、external verifier、structured context 等相关研究。

---

### 3. 如何验证 LLM 生成的计划？

例如：

```text
LLM
 ↓
Candidate Plan
 ↓
Rule Engine
 ↓
Duration Model
 ↓
Feasibility Check
 ↓
Final Plan
```

研究：

* verifier
* critic
* constrained generation
* planning validation
* LLM self-critique
* external evaluation

---

### 4. 如何减少 LLM 调用成本？

重点关注：

* LLM routing
* model cascade
* adaptive invocation
* caching
* structured memory
* tool use
* small model / large model routing

### 可支持的系统模块

```text
LLM Router
Agent
Plan Validator
User Context
RAG / Knowledge Retrieval
```

---

# 11. 用户个体差异 / Individual Differences

### 推荐关键词

英文：

* individual differences in learning
* individual differences in task performance
* personalized learning
* learner modeling
* user modeling
* student modeling
* personalized education
* adaptive learning
* personalized task planning

中文：

* 个体差异
* 个性化学习
* 用户建模
* 学习者建模
* 学生模型
* 自适应学习
* 个性化任务规划

### 重点研究

核心问题：

> 为什么同一个任务，不同人的完成时间和完成概率差异巨大？

重点寻找：

* 先验知识
* 技能水平
* 学习速度
* 自我效能
* 注意力
* 学习策略
* 历史表现
* 个体认知差异

### 可转化为 User State

```text
user_skill
user_knowledge
duration_factor
completion_rate
task_preference
time_preference
stress_response
```

### 可能支持的系统模块

```text
User Model
Personalization
LLM Context
Scheduler
```