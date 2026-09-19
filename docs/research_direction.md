# 自适应任务规划系统

## 机器学习与行为科学论文检索指南

## 1. 研究目标

本项目不是简单研究"如何提高学习效率"，而是希望回答：

> **如何利用用户长期执行数据，预测任务完成所需时间、完成概率、压力/负荷变化，并据此动态调整任务计划？**

因此，论文搜索最终需要服务于机器学习建模。研究结果应该最终转换为：

```text
论文
↓
理论变量
↓
可观测指标
↓
数据字段
↓
ML Feature
↓
预测目标
```

---

## 2. 重点研究方向

## 方向一：精力 / Energy / Fatigue

### 推荐关键词

英文：

- mental energy
- subjective energy
- cognitive fatigue
- mental fatigue
- perceived fatigue
- cognitive performance
- energy level
- fatigue and task performance
- time of day cognitive performance

中文：

- 精力
- 主观精力
- 精神疲劳
- 认知疲劳
- 心理疲劳
- 精力与任务表现
- 生理节律与认知表现

### 希望回答

1. 精力是否能够预测任务完成效率？
2. 精力是否存在明显的时间周期？
3. 高认知任务是否更依赖高精力状态？
4. 精力下降是否导致任务耗时增加？
5. 精力自评是否可以作为机器学习输入变量？

### 可能转化为 Feature

```text
energy_level
fatigue_level
time_of_day
sleep_duration
sleep_quality
recent_high_cognitive_minutes
```

### 预测目标

```text
actual_duration
completion_probability
```

---

## 3. 拖延 / Procrastination

### 推荐关键词

英文：

- procrastination
- academic procrastination
- task delay
- behavioral delay
- procrastination and task difficulty
- procrastination and self-regulation
- procrastination and temporal motivation
- temporal motivation theory

中文：

- 拖延
- 学业拖延
- 任务拖延
- 自我调节
- 时间动机理论
- 任务难度与拖延

### 重点研究

不要只搜索：

> 如何克服拖延

而应该搜索：

> **什么变量能够预测一个人是否会推迟任务？**

例如：任务难度、任务价值、截止日期距离、即时奖励、失败成本、压力、自我效能、任务厌恶程度。

### 可以转化为

```text
task_difficulty
task_value
deadline_distance
task_aversion
self_efficacy
historical_delay
```

预测：

```text
start_delay
completion_probability
```

---

## 4. 任务拆解 / Task Decomposition

### 推荐关键词

英文：

- task decomposition
- hierarchical task planning
- goal decomposition
- goal setting
- goal hierarchy
- task granularity
- task chunking
- subgoal decomposition

中文：

- 任务拆解
- 目标拆解
- 层级任务规划
- 子目标
- 任务粒度
- 任务分块

### 重点研究

一个任务拆多细最合适？例如"学习高数"拆成"极限"，还是拆成"看视频 / 做例题 / 做练习 / 总结"？

需要研究：

> **任务粒度是否影响完成率、认知负荷和拖延？**

### 可以建立 Feature

```text
task_depth
task_size
subtask_count
estimated_duration
task_complexity
```

---

## 5. 高效完成 / Productivity / Performance

不要泛泛搜索"提高效率"。推荐：

- task performance
- productivity prediction
- task completion time prediction
- human performance prediction
- individual productivity
- performance modeling
- time-on-task
- task completion time
- individual differences in task performance

重点研究：

> **什么变量能够预测一个人完成一个任务需要多长时间？**

这部分直接服务于 `Duration Predictor`，目标：

```text
planned_duration
→
actual_duration
```

---

## 6. 反馈调节 / Feedback Regulation

这是本项目非常重要的方向。推荐关键词：

- feedback control
- adaptive planning
- adaptive scheduling
- feedback-driven planning
- human-in-the-loop
- human feedback
- adaptive goal setting
- closed-loop system
- personalized planning
- personalized scheduling

中文：反馈调节、自适应规划、动态调度、个性化规划、人在回路、闭环控制、反馈驱动。

希望理解：

```text
计划 → 执行 → 反馈 → 状态估计 → 调整
```

这种闭环如何设计。

---

## 7. 压力 / Stress / Goal Completion

推荐关键词：

- stress and task performance
- perceived stress
- workload and performance
- cognitive workload
- mental workload
- stress and productivity
- stress and procrastination
- goal attainment and stress
- workload management

中文：压力、感知压力、心理压力、工作负荷、认知负荷、压力与任务完成、压力与拖延、目标完成与压力。

重点研究：

> 任务负荷增加到什么程度后，完成表现开始下降？

这对于 `Daily Load` 模型非常重要。

---

## 8. 认知负荷 / Cognitive Load

推荐：

- cognitive load theory
- intrinsic cognitive load
- extraneous cognitive load
- germane cognitive load
- cognitive workload
- mental workload
- task complexity and cognitive load

重点：

```text
Task → Cognitive Load → Performance
```

项目目前已经存在"高认知 / 中认知 / 低认知"，但这只是初始规则。未来希望利用用户数据校准：

> "一个人一天到底能承受多少高认知任务？"

---

## 9. 时间段 / Circadian Rhythm / Time of Day

推荐：

- time of day and cognitive performance
- circadian rhythm and cognition
- chronotype and productivity
- time of day task performance
- chronotype and academic performance

重点研究：

> 不同人在不同时间段执行不同类型任务时，表现是否存在系统性差异？

未来可以建立：

```text
task_type + time_of_day + user → completion_probability
```

从而实现：推荐这个用户什么时候做数学。

---

## 10. 学习遗忘 / Memory / Spaced Repetition

推荐：

- forgetting curve
- memory retention
- spaced repetition
- retrieval practice
- spacing effect
- learning retention
- memory decay

注意：不要简单认为"艾宾浩斯遗忘曲线 = 所有人的真实遗忘规律"。应该寻找更加现代的实验研究，比较 spaced repetition / retrieval practice / forgetting / retention / individual differences。

最终可能形成：

```text
knowledge_mastery
last_review
review_count
difficulty
```

用于 `Review Scheduler`。

---

## 11. 用户个体差异 / Individual Differences

这是机器学习部分非常重要、但很容易被忽略的方向。推荐：

- individual differences in learning
- individual differences in task performance
- personalized learning
- learner modeling
- user modeling
- student modeling
- personalized education
- adaptive learning

重点：

> 为什么同一个任务，不同人的完成时间差异巨大？

这直接支撑：

```text
Theoretical Workload + User Model = Personalized Workload
```

---

## 12. 推荐建立的机器学习目标

### Model A：任务耗时预测

Input：task type / task difficulty / task size / user skill / historical duration / time of day / fatigue / cognitive load
Output：`predicted_duration`

### Model B：任务完成概率

Input：task difficulty / deadline distance / duration / stress / energy / recent completion rate / task type / time of day
Output：`P(completion)`

### Model C：压力/负荷响应

Input：daily workload / high_cognitive_minutes / recent_completion_rate / deadline_pressure / sleep / energy
Output：`predicted_stress`

### Model D：推荐时间段

Input：task type / time of day / historical performance / energy / fatigue
Output：`recommended_time_slot`

---

## 13. 搜索论文时必须提取什么

不要只把论文标题和摘要复制回来。每篇论文至少提取：

```text
论文名称：
研究问题：
研究对象：
样本数量：
实验方法：
核心变量：
Independent Variables：
Dependent Variables：
使用的量表：
主要结论：
对我们项目有什么帮助：
可以转化成什么 Feature：
可以预测什么 Target：
论文 DOI / 官方链接：
```

---

## 14. 特别关注数据采集方法

对于机器学习来说：

> **论文里的变量最终能不能被我们的 App 采集？** 比理论本身更重要。

例如论文使用 EEG / fMRI / 心率 / 皮肤电，如果比赛硬件没有这些设备，就不能直接作为系统 Feature。

应该优先寻找：self-report、task logs、completion time、behavioral data、daily diary、experience sampling、smartphone data —— 因为这些数据更容易在 App 中持续采集。

> 本项目已经落地的采集字段见 `docs/ml.md`（Feature 来源映射表）与
> `app/domain/models/execution.py` / `feedback.py`。

---

## 15. 最终希望建立的数据闭环

```text
用户输入目标
        ↓
理论分析
        ↓
理论工作量
        ↓
用户历史数据
        ↓
个体化预测
        ↓
生成计划
        ↓
用户执行
        ↓
实际耗时 / 完成率 / 压力 / 精力 / 拖延
        ↓
User Model Update
        ↓
下一轮预测
        ↓
重新规划
```

最终形成：

> **Theory → Personalization → Execution → Feedback → Model Update → Replanning**

---

## 16. 技术主线

```text
理论模型 + 用户行为模型 + 硬约束 + 任务调度 + 反馈闭环
```

| 组件 | 解决的问题 | 代码位置 |
| --- | --- | --- |
| 理论分析 Agent | 这个东西正常需要多少工作量 | `app/agent/nodes/theoretical_analysis.py` |
| 实际情况分析 Agent | 这个用户实际上需要多少工作量 | `app/agent/nodes/user_situation_analysis.py` |
| ML User Model | 从历史数据中估计差异 | `app/ml/` |
| Scheduler | 把预测转化为日程 | `app/domain/scheduling/scheduler.py` |
| Rule Engine | 保证计划不违反硬约束 | `app/domain/rules/` |
| LangGraph | 编排复杂规划/重排 | `app/agent/graph.py` |

> 不要急着把所有智能都交给 Agent，而是把这套已经验证过的决策逻辑固化成
> 可测试的 Domain + Rule + Scheduler，再让 Agent 和 ML 往里面接。
