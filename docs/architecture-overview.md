# 架构总览（Architecture Overview）

> 本文是**当前代码的权威架构说明**（2026-10 校准）。当本文与旧文档冲突时，以本文为准。
> 配套：`docs/development-handbook.md`（开发指南 + 清理记录）、`docs/replan-trigger-design.md`（重排机制设计）。

---

## 0. 一句话定位

这不是一个待办清单，而是一个**反馈驱动的自适应任务规划系统**：

```
目标(goal) → 理论工作量分析 → 用户实况(画像+ML) → 计划生成(LangGraph)
        → 硬约束校验(RuleEngine) → 排期(Scheduler) → 落库
        → 用户执行 → 反馈 → 更新画像 → 重排(新版本)
```

技术栈：Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · LangGraph · uv（Windows 优先）。

---

## 1. 分层图（实际依赖方向）

```
┌─────────────────────────────────────────────────────────────┐
│ 表现层 / API        app/api/**, app/schemas/**, app/main.py  │  路由、鉴权、校验、
└──────────────────────────────┬──────────────────────────────┘  HTTP 状态映射、OpenAPI
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 应用层 / Application app/application/**                      │  编排、事务、权限、DTO、异常
│   services/  dto/  context/  exceptions.py  preferences.py   │
└───────────┬───────────────────────────────┬─────────────────┘
            │ 旁路调用                        │
            ▼                                ▼
┌───────────────────────────┐   ┌──────────────────────────────┐
│ 旁路 A: app/agent/**       │   │ 旁路 B: app/ml/**            │
│ LangGraph 状态机 + 节点/工具│   │ 预测器 Protocol + 统计 mock  │
└───────────┬───────────────┘   └──────────────┬───────────────┘
            │                                    │
            ▼                                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 领域层 / Domain     app/domain/**                            │  实体、硬约束规则、启发式排期、画像
│   models/  rules/  scheduling/  profile/                     │  纯逻辑，零框架依赖
├─────────────────────────────────────────────────────────────┤
│ 基础层 / Core       app/core/**                              │  配置、JWT/密码、日志
└──────────────────────────────▲──────────────────────────────┘
                               │ 基础设施依赖领域（ORM 引用领域枚举）
┌──────────────────────────────┴──────────────────────────────┐
│ 基础设施 / Infrastructure  app/infrastructure/**             │  SQLAlchemy 模型、仓储、LLM 客户端、模型仓库
└─────────────────────────────────────────────────────────────┘
```

**关于箭头的一句澄清**：README 写作「API → Application → Domain/Core → Infrastructure」，这是**编排调用**方向。真实 import 关系是：`domain` 在最内层（不依赖任何人）；`infrastructure` 依赖 `domain`（ORM 引用领域枚举/`utcnow`）；`application` 依赖 `domain` + `infrastructure`；`api` 依赖 `application`。**只有 `application` 会同时用到 repo / scheduler / rule engine / agent / ml。**

约束（强）：
- `app/core`、`app/domain` **绝不** import FastAPI / SQLAlchemy（已核验：仅注释里出现）。
- `agent` **绝不**碰数据库；所需数据由 `PlanService` 通过 `PlannerContext`/`PlannerState` 注入。
- 仓储**只 `flush()`，绝不 commit**；事务由 service 负责。
- `RuleEngine` 是硬约束的**唯一权威**；Agent/LLM 产物只是 candidate。
- `Scheduler` **绝不调用 LLM**。
- API 不直接返回 ORM/领域对象；经 `app/api/v1/mappers.py` 映射到 `app/schemas`。

---

## 2. 各层职责与文件地图

### 2.1 表现层 `app/api` + `app/schemas`

| 文件 | 作用 |
| --- | --- |
| `app/main.py` | 组合根：`create_app()`、`lifespan`（SQLite 时 `init_db()`）、CORS、`ApplicationError` 全局异常映射、`/health`、挂载 `api_router` |
| `app/api/router.py` | 汇总子路由，加前缀 `/api/v1` |
| `app/api/deps.py` | 依赖注入：`get_db`、各 service 工厂、`get_current_user`(Bearer JWT)、进程级单例 `get_generation_service`；**唯一**组装 LLM/checkpointer 的地方 |
| `app/api/v1/auth.py` | `POST /auth/register`(201)、`POST /auth/login`(200) |
| `app/api/v1/users.py` | `/users/me`(GET/PATCH)、`/users/me/profile`、`/users/me/preferences`(GET/PUT)、`/users/me/situation/trends` |
| `app/api/v1/goals.py` | `GET/POST/PATCH/DELETE /goals[/{id}]` |
| `app/api/v1/plans.py` | 最重的路由：`/plans/generate`、`/plans/preview*`、`/plans/decompose`、`/plans/confirm`、`/plans/generation/{job}/status|events`、`/plans`、`/plans/{id}`、`/plans/{id}/changes`、`/plans/{id}/replan`(+eligibility) |
| `app/api/v1/tasks.py` | `PATCH /plans/{plan_id}/tasks/{task_id}` |
| `app/api/v1/feedback.py` | `POST/GET /plans/{plan_id}/feedback` |
| `app/api/v1/insights.py` | `GET /plans/{plan_id}/insights` |
| `app/api/v1/mappers.py` | 领域/DTO → Schema 的**唯一**映射点 |
| `app/schemas/*` | Pydantic 请求/响应模型（wire contract） |

> 路由顺序坑：`/plans/generation/{job_id}/events` 必须定义在 `/plans/{plan_id}` 之前，否则被整型路径参数吞掉。
> API 层应**无业务逻辑**：校验 → 调 service → 映射。

### 2.2 应用层 `app/application`

| 文件 | 职责 |
| --- | --- |
| `services/plan_service.py`（核心，~940 行） | 落 Goal → 组装特征 → 跑图 → 落 Plan/Task/TaskStandard → commit；`update_task`；`process_feedback_cycle`；`replan_with_agent`；计划版本持久化 |
| `services/generation_service.py` | 生成任务注册表 + SSE 事件回放；preview/adjust 在后台线程跑（各自 DB session） |
| `services/feedback_service.py` | 每日反馈落库 → 刷新记忆/画像 → 触发反馈闭环图 |
| `services/replan_service.py` | 重排资格校验（**按用户**冷却） |
| `services/profile_service.py` | 画像持久化 + EWMA 状态 + `build_user_features` + `replan_decision_for` |
| `services/goal_service.py` | 目标 CRUD |
| `services/auth_service.py` | 注册/登录/JWT/资料 |
| `services/situation_service.py` | 精力/压力/效能趋势 |
| `services/insight_service.py` | 只读分析（完成率、计划vs实际、压力、建议） |
| `services/memory_service.py` | 记忆刷新（best-effort） |
| `context/repo_context_builder.py` | **DB → PlanningContext 的唯一通道**（合并记忆/画像/历史） |
| `dto/*` | 服务层内部契约（非 API schema） |
| `exceptions.py` | 框架无关异常，带 `code` + `http_status`，由 `main.py` 映射 |
| `preferences.py` | 调度偏好默认值与合并逻辑 |

事务归属：service 在逻辑单元结束时 `commit()`；repo 只 `flush()`；`get_db()` 只关闭会话。

### 2.3 领域层 `app/domain`

| 目录 | 内容 |
| --- | --- |
| `models/` | 11 个纯 Pydantic 实体（`User/Goal/Plan/Task/TaskStandard/TaskExecution/Feedback/ReplanEvent/AgentRun/AgentMemory/PredictionLog`）+ `enums.py` + `base.py` |
| `rules/` | `Rule` ABC、`RuleEngine`、`RuleContext`、`RuleViolation`、`default_rules()` + **7 条硬约束**（6 个文件） |
| `scheduling/` | `SchedulerConfig` / `Scheduler`（贪心确定性排期，无 LLM）、`CandidateSchedule`/`ScheduledTask`（`ScheduleResult` 已删） |
| `profile/` | 纯画像引擎：`engine.py`（resolve/init/update/predict/replan）、`mbti_templates.py`、`models.py`（frozen dataclass） |

7 条硬约束（`default_rules()` 注册，`name`/`code` 唯一）：

| 规则 | 文件 | code |
| --- | --- | --- |
| 高认知不连续 + 每日高认知上限 | `cognitive_load.py` | `high_cognitive_consecutive` / `high_cognitive_daily_max` |
| 同学科冲突不得同日 | `same_day_conflict.py` | `same_day_conflict` |
| 每日总时长上限 | `daily_limit.py` | `daily_limit` |
| 每日可用时长 + 时间窗 | `daily_limit.py` | `available_time` / `outside_available_window` |
| 任务间缓冲 | `buffer_time.py` | `insufficient_buffer` |
| 不得排到 DDL 之后 | `deadline.py` | `deadline_exceeded` |
| 已完成任务不得重排 | `completed_tasks.py` | `completed_task_rescheduled` |

### 2.4 基础设施 `app/infrastructure`

| 目录 | 内容 |
| --- | --- |
| `database/session.py` | `engine`、`SessionLocal`、`session_scope()`、`init_db()`（仅 SQLite 由 lifespan 调用） |
| `database/models/` | 12 个 SQLAlchemy ORM 模型（领域模型的镜像） |
| `database/repositories/` | 13 个仓储，flush-only，ORM ↔ 领域双向转换 |
| `llm/client.py` | `LLMClient` Protocol、`MockLLMClient`（默认）、`HttpLLMClient`、进程级缓存 `get_llm_client` |
| `ml/model_store.py` | `ModelStore` Protocol + InMemory/File 实现，**占位，无调用者**（刻意保留的接缝，见开发指南） |

### 2.5 旁路 A：`app/agent`（LangGraph 编排）

**两个图**（`app/agent/graph.py`，按 checkpointer 构建并缓存；`langgraph` 缺失时降级为顺序执行器）：

- **图 A：初始计划**（`initial-plan-v1`）
  `START → load_context → classify_request → goal_analysis → theoretical_analysis → user_situation_analysis → plan_generation → rule_validation`
  `rule_validation --(should_repair)--> plan_repair → rule_validation`（有界循环）
  `rule_validation → preview --(route_after_preview)--> plan_generation | plan_finalization → END`
  *（`preview` 用 LangGraph `interrupt` 实现 preview/confirm/adjust 人工回路）*
- **图 B：反馈闭环**（`feedback-loop-v1`）
  `START → load_context → process_feedback → ml_prediction → adjustment_router`
  `adjustment_router --(route_after_adjustment)--> END | micro_adjustment → rule_validation | goal_analysis → … → new_plan → END`

节点文件（`app/agent/nodes/`）：`context`(load_context)、`classify`、`goal_analysis`、`theoretical_analysis`、`user_situation`、`plan_generation`、`validation`(rule_validation)、`repair`、`preview`、`finalization`、`prediction`(ml_prediction)、`adjustment_router`、`micro_adjustment`、`feedback`(process_feedback)、`replan`(new_plan)、`_shared`(工具函数)。

工具（`app/agent/tools/`，注册 7 个）：`task_decomposer`、`workload_estimator`、`plan_drafter`、`schedule_generator`、`rule_validator`、`memory_retriever`、`task_duration_predictor`。

记忆（`app/agent/memory/`，纯函数）：`build_semantic_memory` / `build_episodic_memory` / `derive_procedural_memory`；读侧在 `repo_context_builder`，写侧在 `memory_service`。图本身不 import 它们（架构规则成立）。

### 2.6 旁路 B：`app/ml`（预测器接口 + 统计 mock）

`base.py` 定义 4 个 `@runtime_checkable Protocol`（Duration/Completion/Stress/TimeSlot）+ 契约模型；`predictors.py::PredictorSet.default()` 组装；`*_predictor.py` 是**纯统计实现**，`source="mock:statistical"`；`adjustment.py` 提供 `RuleBasedAdjustmentPredictor`（默认）与 `MockAdjustmentPredictor`（测试）。

---

## 3. 核心数据模型与关系

12 个 ORM 模型（`app/infrastructure/database/models/`），与领域实体 1:1 镜像（`UserStateModel` 的领域对应是 `domain/profile/models.py::UserStateData`）：

```
User 1──* Goal 1──* Task 1──* TaskStandard
User 1──* Plan 1──* Task
Plan  ──self (parent_plan_id → 版本链)   Task ──self (parent_task_id → 子任务)
Task 1──* TaskExecution
Plan 1──* Feedback        User 1──* Feedback
Plan 1──* ReplanEvent
UserStateModel (user_id unique, 1 行/用户, 无 relationship)
AgentRun / AgentMemory / PredictionLog（日志型，FK users.id，无 relationship）
```

关键约束：`plans(user_id, version)` unique；`agent_memories(user_id, kind, key)` unique；index `tasks(plan_id, scheduled_date)`。
`ReplanTriggerType` 枚举：`manual / feedback_triggered / scheduled / system`。
`TaskExecution` 是**ML 数据资产**（计划 vs 实际耗时、完成率、压力前后、难度、失败原因、时间段）。

---

## 4. 两条主链路

### 4.1 生成计划：`POST /api/v1/plans/generate`（真异步 job + 实时 SSE）

```
API validate → GenerationService.submit(kind="generate")  ← 立即返回 202
  └─ 后台线程 _run_job（自己的 DB session）
       └─ PlanService.generate_plan_with_events
            ├─ _persist_goals           先落 Goal，拿真 id，建 goal_id_map{index+1: goal_id}
            ├─ RepoContextBuilder       读历史/画像/记忆 → PlanningContext（唯一 DB→context 通道）
            ├─ PlannerGraph 跑图 A        load_context → … → plan_generation → rule_validation(→repair)
            ├─ confirm_plan             resume 图 A → plan_finalization
            └─ _persist_final_plan      落 Plan(版本) / Task / TaskStandard → commit
节点 ctx.publish(...) → PlanService._run 镜像到 emit → job.events → SSE 实时推送
GET /plans/generation/{job_id}/events  实时 SSE（event: <节点名>），最后 completed 带 result
```

同样改为真异步 job 的还有 `POST /plans/decompose`、`POST /plans/{id}/replan`；
`POST /plans/preview`、`/plans/preview/{thread_id}/adjust` 本来就是真异步。
两个 `confirm` 仍同步（快速落库）。反馈可选用 `?stream_replan=true` 让重排图走 job。
详细契约见 `docs/streaming-and-callchains.md`。

### 4.2 反馈 → 重排：`POST /plans/{plan_id}/feedback`

```
FeedbackService.submit_feedback
  ├─ 落 Feedback 行（commit）
  ├─ MemoryService.refresh（best-effort）
  ├─ ProfileService.update_from_feedback（EWMA 更新 user_states，best-effort）
  └─ PlanService.process_feedback_cycle → 图 B
        process_feedback → ml_prediction → adjustment_router
          ├─ NO_CHANGE → END
          ├─ MICRO_ADJUST → micro_adjustment → rule_validation → new_plan
          └─ FULL_REPLAN → goal_analysis → … → new_plan
     若产生新计划：落 v(n+1)、旧版 superseded、parent_plan_id、写 ReplanEvent
```

> 重排触发的精确逻辑与问题诊断，见 `docs/replan-trigger-design.md`（**重要**）。

---

## 5. 必须记住的不变量

1. **临时任务 id = `order_index + 1`**：图运行时任务尚未落库。`drafts_to_tasks` / `build_rule_context` / `CandidateSchedule` / `plan_repair` 全部用同一规则；`_persist_plan` 落库后映射成真实 PK。
2. **SSE stage 名 = 节点名**（`goal_analysis`…`plan_repair`）+ 最后 `completed`；由 `GenerationEvent.stage` 生成。
3. **计划版本不可变**：重排只新增 `v(n+1)`，旧版置 `superseded`，`parent_plan_id` 串联，写 `ReplanEvent`。
4. **重排冷却按用户**（不是按计划）：`ReplanEventRepository.get_latest_for_user` + `SCHEDULER_MIN_REPLAN_INTERVAL_HOURS`。
5. **一切同步**：service/agent/repository/predictor/`LLMClient.complete` 都是 `def`；只有 SSE 路由是 async。
6. **Provisional/goal 键**：`goal_id_map` 的键是 1-based 的请求内目标序号。

---

## 6. 组合根、事务与配置

- 组合根两处曾重复，现已合并：`app/api/deps.py` 是**唯一**组装 LLM/checkpointer/GenerationService 的地方（`generation_service._default_service_factory` 已删）。
- `get_settings()` 有 `lru_cache`；改 `.env` 需重启或 `get_settings.cache_clear()`。
- SQLite 由 lifespan `init_db()` 建表；Postgres 走 Alembic（`alembic/env.py` 读 `Settings`，无 URL 写死在 ini）。

---

## 7. 扩展接缝（设计为可替换）

| 要替换 | 改哪里 | 不动 |
| --- | --- | --- |
| LLM | 实现 `LLMClient`（`infrastructure/llm/client.py`），设 `LLM_PROVIDER` | 节点契约（`llm=None` 即可跑确定性流程） |
| 某个 Agent | 改对应 `nodes/<node>.py` 内的实现 | 图结构、`PlannerState`/`PlannerContext` |
| 真实 ML | 在 `app/ml/` 实现 4 个 Protocol，`PlanService(predictors=…)` 注入 | service / API / DB |
| 排期算法 | `domain/scheduling/scheduler.py::Scheduler.schedule` | 规则、服务 |
| 数据库 | `infrastructure/database/repositories/*` | 领域层、服务层 |
| 新增硬约束 | `domain/rules/<new>.py` + 在 `default_rules()` 注册 | 服务层、API |
| 新增 API | `api/v1/<res>.py` + `router.py` + `schemas/<res>.py` + `mappers.py` | 领域层 |
| 新增字段 | **同时**改 `domain/models/<x>.py`、`infrastructure/database/models/<x>.py`、`schemas/<x>.py`、迁移 | 只改一处会漂移 |

---

## 8. 文档地图

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| **本文件 `architecture-overview.md`** | ✅ 权威 | 分层、数据模型、主链路 |
| **`development-handbook.md`** | ✅ 权威 | 开发指南 + 清理记录 + 已知缺陷 |
| **`replan-trigger-design.md`** | ✅ 权威 | 重排触发设计 + 未决问题 |
| **`product-painpoints.md`** | ✅ 权威 | 痛点与需求建议 |
| `modules.md` | ⚠️ 部分过时 | 逐模块详解，仍有用；但引用了已删的 `user_model_service.py`/`UserModelService`/`get_logger`/`schedule_tasks`/`ScheduleResult`/`user_statistics`/`run_with_events`/`repair.md` |
| `architecture.md` / `langgraph.md` | ⚠️ 过时 | `langgraph.md` 已自标 SUPERSEDED；`architecture.md` 仍提 `UserModelService`/9 个 ORM/`app/ml/user_model.py` |
| `domain.md` | ⚠️ 部分过时 | 含 `UserModel` 章节（表已删） |
| `agent/*`、`user-portrait.md`、`ml.md`、`api*.md`、`development.md`、`database/*` | ✅ 基本可用 | 与当前实现一致或差异很小 |
