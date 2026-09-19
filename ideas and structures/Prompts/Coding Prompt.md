你是一名资深 Python 后端架构师，请为一个“AI 自适应任务规划系统”搭建第一版 FastAPI 后端工程骨架。

## 一、项目背景

这是一个基于用户真实执行反馈持续调整任务计划的 AI 自适应任务规划系统。

用户输入：

* 长期目标 + DDL
* 短期目标 + DDL
* 可选的行动力/执行能力权重
* 可用时间、作息等信息

系统经过：

目标拆解 → 理论任务工作量分析 → 用户实际情况分析 → 计划生成 → 用户执行 → 反馈 → 用户模型更新 → 动态重排

形成闭环。

系统不是传统 Todo List，而是“反馈驱动的自适应任务规划系统”。

核心思想：

> 理论任务工作量 + 用户历史执行数据 + ML 用户模型 + 硬约束规则 → 生成适合当前用户的计划。

---

# 二、技术栈

请使用：

* Python 3.12+
* FastAPI
* Pydantic v2
* SQLAlchemy 2.x
* Alembic
* PostgreSQL（如果本地开发方便，可以提供 SQLite 开发配置）
* JWT Authentication
* LangGraph
* httpx
* pytest

依赖管理优先使用 uv。

不要引入不必要的大型框架。

---

# 三、架构原则

采用分层架构：

Frontend
↓
API / Presentation
↓
Application / Service
↓
Domain / Core
↓
Infrastructure

核心原则：

1. Core 不依赖 FastAPI
2. Core 不依赖 SQLAlchemy
3. Core 不直接访问数据库
4. Agent 不直接访问数据库
5. Service 负责业务流程编排、事务、权限和调用 Agent/ML/Rule
6. Rule Engine 负责硬约束
7. ML Scheduler 负责预测基础上的具体排期
8. LangGraph 负责复杂规划流程
9. 所有 Agent 输出必须结构化
10. 不要让 LLM 直接决定硬约束是否满足

---

# 四、推荐目录结构

请按照类似以下结构创建：

app/
├── main.py
│
├── api/
│   ├── deps.py
│   ├── router.py
│   └── v1/
│       ├── auth.py
│       ├── users.py
│       ├── plans.py
│       ├── feedback.py
│       ├── tasks.py
│       └── insights.py
│
├── application/
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── plan_service.py
│   │   ├── feedback_service.py
│   │   ├── replan_service.py
│   │   └── user_model_service.py
│   └── dto/
│
├── domain/
│   ├── models/
│   │   ├── user.py
│   │   ├── goal.py
│   │   ├── plan.py
│   │   ├── task.py
│   │   ├── task_standard.py
│   │   ├── feedback.py
│   │   ├── execution.py
│   │   └── user_model.py
│   │
│   ├── rules/
│   │   ├── base.py
│   │   ├── cognitive_load.py
│   │   ├── daily_limit.py
│   │   ├── buffer_time.py
│   │   └── same_day_conflict.py
│   │
│   └── scheduling/
│       ├── scheduler.py
│       └── schedule_result.py
│
├── core/
│   ├── config.py
│   ├── security.py
│   └── logging.py
│
├── agent/
│   ├── graph.py
│   ├── state.py
│   ├── nodes/
│   │   ├── goal_analysis.py
│   │   ├── theoretical_analysis.py
│   │   ├── user_situation_analysis.py
│   │   ├── plan_generation.py
│   │   ├── rule_validation.py
│   │   └── plan_repair.py
│   └── schemas.py
│
├── ml/
│   ├── base.py
│   ├── duration_predictor.py
│   ├── completion_predictor.py
│   ├── stress_predictor.py
│   ├── time_predictor.py
│   └── user_model.py
│
├── infrastructure/
│   ├── database/
│   │   ├── session.py
│   │   ├── models/
│   │   └── repositories/
│   │
│   ├── llm/
│   │   └── client.py
│   │
│   └── ml/
│       └── model_store.py
│
└── schemas/
├── auth.py
├── user.py
├── plan.py
├── task.py
├── feedback.py
└── common.py

tests/
├── unit/
├── integration/
└── api/

docs/
├── architecture.md
├── api.md
├── langgraph.md
├── domain.md
└── development.md

alembic/
pyproject.toml
.env.example
README.md
docker-compose.yml

````

可以根据实际情况调整目录，但必须保持“API / Application / Domain / Infrastructure”职责清晰。

---

# 五、数据库模型

至少设计：

## User

id
email
password_hash
created_at

## Goal

id
user_id
title
description
goal_type
deadline
priority
status

## Plan

id
user_id
version
status
start_date
end_date
created_at

## Task

id
plan_id
goal_id
parent_task_id
title
description
estimated_duration
predicted_duration
cognitive_load
priority
scheduled_date
start_time
end_time
status

## TaskStandard

id
task_id
description
estimated_duration
completed

## TaskExecution

记录真实执行数据，是未来机器学习的重要数据资产：

id
task_id
user_id
planned_duration
actual_duration
completion_rate
started_at
finished_at
difficulty_feedback
stress_before
stress_after
failure_reason
time_of_day
completed

## Feedback

id
user_id
plan_id
date
completion_rate
stress_level
energy_level
delay_reason
free_text
created_at

## UserModel

id
user_id
model_version
duration_factors
completion_probability
stress_response
preferred_time_slots
updated_at

## ReplanEvent

id
plan_id
trigger_type
reason
old_version
new_version
created_at

数据库模型要支持未来机器学习训练，但第一版不要实现复杂 ML。

---

# 六、RESTful API

实现 OpenAPI 自动文档，并保证 `/docs` 和 `/redoc` 可访问。

API：

POST
/api/v1/auth/register

POST
/api/v1/auth/login

GET
/api/v1/users/me

POST
/api/v1/plans/generate

GET
/api/v1/plans

GET
/api/v1/plans/{plan_id}

POST
/api/v1/plans/{plan_id}/feedback

GET
/api/v1/plans/{plan_id}/feedback

POST
/api/v1/plans/{plan_id}/replan

GET
/api/v1/plans/{plan_id}/replan/eligibility

GET
/api/v1/plans/{plan_id}/insights

PATCH
/api/v1/plans/{plan_id}/tasks/{task_id}

对于每个 API：

- 使用 Pydantic Request/Response Schema
- 不直接暴露 ORM Model
- 给出明确 HTTP Status Code
- 给出错误响应模型
- 给出接口 summary / description
- 给出请求参数说明
- 给出 response schema
- 使用 OpenAPI tags 分类

---

# 七、SSE

计划生成需要支持流式状态：

POST /plans/generate

可以先同步返回 job/task id，然后：

GET /api/v1/plans/generation/{job_id}/events

通过 SSE 推送：

goal_analysis
theoretical_analysis
user_situation_analysis
plan_generation
rule_validation
plan_repair
completed

每个 event 都使用结构化 JSON。

第一版可以使用 mock generator，但必须把接口设计好。

---

# 八、LangGraph

设计一个明确的状态机。

核心流程：

START
↓
Goal Analysis
↓
Theoretical Analysis
↓
User Situation Analysis
↓
Plan Generation
↓
Rule Validation
↓
是否违反硬约束？

No → END

Yes
↓
Plan Repair
↓
Rule Validation
↓
END

State 至少包括：

- user_id
- goals
- user_profile
- theoretical_workload
- predicted_duration
- predicted_completion_probability
- stress_estimation
- candidate_plan
- rule_violations
- repaired_plan
- final_plan
- confidence

请在 `docs/langgraph.md` 中解释每个 Node 的输入、输出和职责。

注意：

LangGraph 负责流程编排，不负责数据库事务。

---

# 九、理论分析 Agent

设计接口：

TheoreticalAnalysisAgent

职责：

根据任务内容估算：

- 学习/工作内容
- 子任务
- 理论工作量
- 视频/阅读时间
- 练习时间
- 总理论时间
- 难度
- 认知负荷

输出必须为 Pydantic 结构化对象。

第一版允许使用 Mock 实现。

---

# 十、实际情况分析 Agent

设计：

UserSituationAnalysisAgent

输入：

- 用户历史 TaskExecution
- Feedback
- UserModel
- 当前任务

输出：

- 用户实际耗时倍率
- 当前完成能力
- 当前压力状态
- 当前疲劳/负荷状态
- 推荐时段
- 预测任务耗时
- 预测完成概率
- 是否需要降低任务量

第一版使用简单统计方法 Mock 实现。

不要把 ML 写死在 Agent 中。

---

# 十一、ML 接口

设计统一 Protocol / Interface：

DurationPredictor
CompletionPredictor
StressPredictor
TimeSlotPredictor

第一版提供：

RuleBased / Statistical Mock 实现。

例如：

predicted_duration =
theoretical_duration × user_duration_factor

以后可以替换成：

LightGBM / XGBoost / PyTorch / sklearn 等模型，而无需修改 Service 和 API。

---

# 十二、Rule Engine

必须支持硬约束。

第一版实现：

1. 高认知任务不连续
2. 数学与算法不能安排在同一天
3. 每日总任务时长上限
4. 任务之间必须存在缓冲时间
5. 不得超过用户可用时间
6. DDL 不得被安排超过
7. 已完成任务不得重新安排

设计：

Rule
↓
validate(schedule)
↓
RuleViolation[]

规则必须返回结构化 violation：

{
  "rule": "...",
  "severity": "hard",
  "task_ids": [],
  "message": "..."
}

---

# 十三、Scheduler

Scheduler 不调用 LLM。

输入：

- Tasks
- Predicted duration
- Completion probability
- User state
- Available time
- Rules

输出：

Candidate Schedule

然后交给 Rule Engine 验证。

目标：

- 尽量满足 DDL
- 控制每日负荷
- 最大化完成概率
- 避免高认知任务连续
- 留出缓冲
- 避免计划过载

第一版可以采用 heuristic scheduling，不需要复杂优化算法。

---

# 十四、Service 层

至少实现：

PlanService.generate_plan()
PlanService.get_plan()
FeedbackService.submit_feedback()
ReplanService.check_eligibility()
ReplanService.replan()
UserModelService.update_model()

Service 负责：

- 权限检查
- 事务
- 调用 Repository
- 调用 Scheduler
- 调用 Rule Engine
- 调用 Agent
- 调用 ML
- 保存 Plan Version
- 创建 ReplanEvent

---

# 十五、Plan Version

计划必须支持版本：

v1
v2
v3
...

重排不能覆盖旧计划。

例如：

Plan v1
↓
Feedback
↓
Replan
↓
Plan v2

保留：

- trigger
- reason
- changed_tasks
- old_version
- new_version

这样未来可以分析“为什么计划发生变化”。

---

# 十六、开发原则

现在目标是“可运行的工程骨架”，不是一次实现完整 AI 系统。

因此：

不要：

- 过度实现 ML
- 编造不存在的算法
- 创建复杂微服务
- 引入 Kafka / Redis Cluster / Kubernetes
- 引入向量数据库
- 让 Agent 直接操作 DB
- 把所有业务都交给 LLM

需要：

- 完整项目结构
- 可运行 FastAPI
- PostgreSQL / SQLite 开发配置
- Alembic
- JWT
- Repository
- Service
- Domain
- Rule Engine
- Scheduler
- Mock Agent
- LangGraph 状态机
- Mock ML
- OpenAPI
- pytest 基础测试
- Docker Compose
- README
- `.env.example`

---

# 十七、必须生成的文档

## docs/architecture.md

说明：

Frontend
→ API
→ Application
→ Domain
→ Infrastructure

以及模块职责和依赖关系。

## docs/api.md

说明所有 REST API。

## docs/langgraph.md

说明 LangGraph State、Node、Edge 和状态流转。

## docs/ml.md

说明：

理论工作量
→ 用户实际数据
→ 耗时预测
→ 完成概率
→ 压力响应
→ Scheduler

以及未来替换 ML 模型的接口。

## docs/development.md

说明本地：

uv
数据库
Alembic
启动 FastAPI
运行测试
访问 OpenAPI

---

# 十八、最终要求

完成后请：

1. 输出完整项目目录树
2. 创建所有必要文件
3. 保证项目可以启动
4. 保证 `/docs` 可访问
5. 保证数据库可以初始化
6. 保证 Alembic 可以运行
7. 提供 `.env.example`
8. 提供 Docker Compose
9. 提供基础 pytest
10. 提供 README
11. 不要伪造已经实现的 ML 能力
12. 对 Mock / Placeholder 明确标记
13. 保持代码模块化，使后续可以独立替换：
   - LLM
   - LangGraph Agent
   - ML Model
   - Scheduler
   - Database

最后，请检查一次 import、类型错误和项目启动路径，并确保这是一个真正可以作为后续 React Native 前端、Agent 开发和 ML 开发基础的 FastAPI 项目，而不是仅用于展示的代码样例。

---

# 十四、然后这是给「信息搜索组」的 MD

这个我建议你们不要让同学直接搜索：

> “如何提高效率”

这种关键词太宽。

你们真正需要的是建立：

```text
科学研究
↓
变量
↓
可测量指标
↓
数据字段
↓
ML Feature
````

比如：

```text
“精力”
↓
energy level
↓
时间段 / 自评精力 / 睡眠 / 历史表现
↓
数据库字段
↓
推荐时段模型
```

下面这个可以直接作为 `research_direction.md`。

# 自适应任务规划系统

## 机器学习与行为科学论文检索指南

## 1. 研究目标

本项目不是简单研究“如何提高学习效率”，而是希望回答：

> **如何利用用户长期执行数据，预测任务完成所需时间、完成概率、压力/负荷变化，并据此动态调整任务计划？**

因此，论文搜索最终需要服务于机器学习建模。

研究结果应该最终转换为：

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

# 2. 重点研究方向

## 方向一：精力 / Energy / Fatigue

### 推荐关键词

英文：

* mental energy
* subjective energy
* cognitive fatigue
* mental fatigue
* perceived fatigue
* cognitive performance
* energy level
* fatigue and task performance
* time of day cognitive performance

中文：

* 精力
* 主观精力
* 精神疲劳
* 认知疲劳
* 心理疲劳
* 精力与任务表现
* 生理节律与认知表现

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

# 3. 拖延 / Procrastination

### 推荐关键词

英文：

* procrastination
* academic procrastination
* task delay
* behavioral delay
* procrastination and task difficulty
* procrastination and self-regulation
* procrastination and temporal motivation
* temporal motivation theory

中文：

* 拖延
* 学业拖延
* 任务拖延
* 自我调节
* 时间动机理论
* 任务难度与拖延

### 重点研究

不要只搜索：

> 如何克服拖延

而应该搜索：

> **什么变量能够预测一个人是否会推迟任务？**

例如：

* 任务难度
* 任务价值
* 截止日期距离
* 即时奖励
* 失败成本
* 压力
* 自我效能
* 任务厌恶程度

### 可以转化为：

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

# 4. 任务拆解 / Task Decomposition

### 推荐关键词

英文：

* task decomposition
* hierarchical task planning
* goal decomposition
* goal setting
* goal hierarchy
* task granularity
* task chunking
* subgoal decomposition

中文：

* 任务拆解
* 目标拆解
* 层级任务规划
* 子目标
* 任务粒度
* 任务分块

### 重点研究

一个任务拆多细最合适？

例如：

```text
学习高数
```

拆成：

```text
极限
```

还是：

```text
看视频
做例题
做练习
总结
```

需要研究：

> **任务粒度是否影响完成率、认知负荷和拖延？**

### 可以建立 Feature：

```text
task_depth
task_size
subtask_count
estimated_duration
task_complexity
```

---

# 5. 高效完成 / Productivity / Performance

不要泛泛搜索“提高效率”。

推荐：

* task performance
* productivity prediction
* task completion time prediction
* human performance prediction
* individual productivity
* performance modeling
* time-on-task
* task completion time
* individual differences in task performance

重点研究：

> **什么变量能够预测一个人完成一个任务需要多长时间？**

这部分直接服务于：

```text
Duration Predictor
```

目标：

```text
planned_duration
→
actual_duration
```

---

# 6. 反馈调节 / Feedback Regulation

这是本项目非常重要的方向。

推荐关键词：

* feedback control
* adaptive planning
* adaptive scheduling
* feedback-driven planning
* human-in-the-loop
* human feedback
* adaptive goal setting
* closed-loop system
* personalized planning
* personalized scheduling

中文：

* 反馈调节
* 自适应规划
* 动态调度
* 个性化规划
* 人在回路
* 闭环控制
* 反馈驱动

希望理解：

```text
计划
↓
执行
↓
反馈
↓
状态估计
↓
调整
```

这种闭环如何设计。

---

# 7. 压力 / Stress / Goal Completion

推荐关键词：

* stress and task performance
* perceived stress
* workload and performance
* cognitive workload
* mental workload
* stress and productivity
* stress and procrastination
* goal attainment and stress
* workload management

中文：

* 压力
* 感知压力
* 心理压力
* 工作负荷
* 认知负荷
* 压力与任务完成
* 压力与拖延
* 目标完成与压力

重点研究：

> 任务负荷增加到什么程度后，完成表现开始下降？

这对于：

```text
Daily Load
```

模型非常重要。

---

# 8. 认知负荷 / Cognitive Load

推荐：

* cognitive load theory
* intrinsic cognitive load
* extraneous cognitive load
* germane cognitive load
* cognitive workload
* mental workload
* task complexity and cognitive load

重点：

```text
Task
↓
Cognitive Load
↓
Performance
```

项目目前已经存在：

```text
高认知
中认知
低认知
```

但这只是初始规则。

未来希望利用用户数据校准：

> “一个人一天到底能承受多少高认知任务？”

---

# 9. 时间段 / Circadian Rhythm / Time of Day

推荐：

* time of day and cognitive performance
* circadian rhythm and cognition
* chronotype and productivity
* time of day task performance
* chronotype and academic performance

重点研究：

> 不同人在不同时间段执行不同类型任务时，表现是否存在系统性差异？

未来可以建立：

```text
task_type
+
time_of_day
+
user
→
completion_probability
```

从而实现：

> 推荐这个用户什么时候做数学。

---

# 10. 学习遗忘 / Memory / Spaced Repetition

推荐：

* forgetting curve
* memory retention
* spaced repetition
* retrieval practice
* spacing effect
* learning retention
* memory decay

注意：

不要简单认为：

> 艾宾浩斯遗忘曲线 = 所有人的真实遗忘规律。

应该寻找更加现代的实验研究，比较：

* spaced repetition
* retrieval practice
* forgetting
* retention
* individual differences

最终可能形成：

```text
knowledge_mastery
last_review
review_count
difficulty
```

用于：

```text
Review Scheduler
```

---

# 11. 用户个体差异 / Individual Differences

这是机器学习部分非常重要、但很容易被忽略的方向。

推荐：

* individual differences in learning
* individual differences in task performance
* personalized learning
* learner modeling
* user modeling
* student modeling
* personalized education
* adaptive learning

重点：

> 为什么同一个任务，不同人的完成时间差异巨大？

这直接支撑：

```text
Theoretical Workload
+
User Model
=
Personalized Workload
```

---

# 12. 推荐建立的机器学习目标

根据论文搜索结果，最终尝试建立以下模型。

## Model A：任务耗时预测

Input：

```text
task type
task difficulty
task size
user skill
historical duration
time of day
fatigue
cognitive load
```

Output：

```text
predicted_duration
```

---

## Model B：任务完成概率

Input：

```text
task difficulty
deadline distance
duration
stress
energy
recent completion rate
task type
time of day
```

Output：

```text
P(completion)
```

---

## Model C：压力/负荷响应

Input：

```text
daily workload
high_cognitive_minutes
recent_completion_rate
deadline_pressure
sleep
energy
```

Output：

```text
predicted_stress
```

---

## Model D：推荐时间段

Input：

```text
task type
time of day
historical performance
energy
fatigue
```

Output：

```text
recommended_time_slot
```

---

# 13. 搜索论文时必须提取什么

不要只把论文标题和摘要复制回来。

每篇论文至少提取：

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

# 14. 特别关注数据采集方法

对于机器学习来说：

> **论文里的变量最终能不能被我们的 App 采集？**

比理论本身更重要。

例如论文使用：

```text
EEG
fMRI
心率
皮肤电
```

如果比赛硬件没有这些设备，就不能直接作为系统 Feature。

应该优先寻找：

```text
self-report
task logs
completion time
behavioral data
daily diary
experience sampling
smartphone data
```

因为这些数据更容易在 App 中持续采集。

---

# 15. 最终希望建立的数据闭环

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
实际耗时
完成率
压力
精力
拖延
        ↓
User Model Update
        ↓
下一轮预测
        ↓
重新规划
```

最终形成：

> **Theory → Personalization → Execution → Feedback → Model Update → Replanning**

这就是论文检索最终需要服务的系统闭环。

---

## 最后，我会把你们现在的整个系统定成这一句话

你们真正的技术主线其实可以压缩成：

```text
理论模型
    +
用户行为模型
    +
硬约束
    +
任务调度
    +
反馈闭环
```

其中：

**理论分析 Agent**解决“这个东西正常需要多少工作量”。

**实际情况分析 Agent**解决“这个用户实际上需要多少工作量”。

**ML User Model**负责从历史数据中越来越准确地估计这个差异。

**Scheduler**负责把预测转化为日程。

**Rule Engine**负责保证计划不会违反硬约束。

**LangGraph**负责那些需要复杂推理的规划/重排过程。

这五个东西的职责非常清楚以后，你们这个项目就不会变成一个“LLM 到处调用”的 Demo，而会变成一个**LLM + ML + 规则 + 调度 + 用户反馈数据真正结合起来的系统**。

而且这和你们暑假已经验证过的核心闭环是连续的：你们原来的系统已经有每日反馈、认知负荷、可量化完成标准和动态重排，只是此前主要靠 Markdown + Prompt，现在是在把它工程化。 目前最大的价值反而是**不要急着把所有智能都交给 Agent，而是把这套已经验证过的决策逻辑固化成可测试的 Domain + Rule + Scheduler，再让 Agent 和 ML 往里面接。**
