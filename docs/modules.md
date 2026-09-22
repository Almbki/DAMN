# app 模块详解（开发与调试指南）

> 目的：逐模块说明 `app/` 下每个文件的**作用、所属层、上下游依赖**，并给出一条完整调用链和调试清单。
> 配套阅读：`docs/architecture.md`（英文架构）、`AGENTS.md`（命令与硬规则）。

---

## 0. 分层与依赖方向（先看这个）

```
表现层     app/api/**        app/schemas/**        app/main.py
                 │                  ▲
                 ▼                  │ 映射 DTO→Schema
应用层     app/application/**  (services + dto + exceptions)
                 │
                 ├──────────────► app/agent/**   （旁路：LangGraph 编排）
                 ├──────────────► app/ml/**      （旁路：预测器 Protocol + 统计 mock）
                 ▼
领域层     app/domain/**     （models + rules + scheduling）
基础层     app/core/**       （config + security + logging）
                 ▲
基础设施   app/infrastructure/**（SQLAlchemy + repositories + LLM + model store）
```

**依赖只能向下**：`core` / `domain` 绝不 import FastAPI 或 SQLAlchemy；
`agent` 绝不碰数据库；只有 `application` 会同时调用 repo、scheduler、rule engine、agent、ml。

| 目录 | 所属层 | 一句话职责 |
| --- | --- | --- |
| `app/core` | 基础层 | 配置、JWT/密码、日志，无框架依赖 |
| `app/domain` | 领域层 | 实体、硬约束规则、启发式排期，纯逻辑 |
| `app/ml` | 旁路（被应用层驱动） | 四个预测器接口 + 统计 mock |
| `app/agent` | 旁路（被应用层驱动） | LangGraph 状态机 + 各节点 Agent |
| `app/infrastructure` | 基础设施层 | ORM/仓储/LLM/模型仓库 |
| `app/application` | 应用层 | 业务流程编排、事务、权限、DTO、异常 |
| `app/api` + `app/schemas` | 表现层 | 路由、依赖注入、请求/响应模型 |
| `app/main.py` | 组合根 | 组装 FastAPI、lifespan、异常映射、路由挂载 |

---

## 1. 一次 `POST /api/v1/plans/generate` 的完整调用链（调试主线）

```
app/main.py::create_app
  └─ api/router.py::api_router
      └─ api/v1/plans.py::generate_plan
          ├─ api/deps.py::get_current_user        → core/security.py::decode_access_token
          │                                          application/services/auth_service.py::get_user
          ├─ api/v1/plans.py::_to_generation_request → agent/state.py::GenerationRequest
          ├─ api/deps.py::get_generation_service     →（进程级单例）GenerationService
          └─ application/services/generation_service.py::create_job
              └─ application/services/plan_service.py::generate_plan_with_events
                  ├─ infrastructure/.../repositories/goal_repository.py::create_many（先落 Goal，拿真 id）
                  ├─ application/services/user_model_service.py::get_user_features
                  │     ├─ execution/feedback repository（读历史）
                  │     └─ ml/user_model.py::StatisticalUserModelBuilder.to_features
                  ├─ agent/graph.py::PlannerGraph.run_with_events        ← 打开 LangGraph
                  │     ├─ nodes/goal_analysis.py::goal_analysis_node
                  │     ├─ nodes/theoretical_analysis.py::theoretical_analysis_node
                  │     ├─ nodes/user_situation_analysis.py::user_situation_analysis_node
                  │     │     └─ ml/predictors.py::PredictorSet.default() 的 4 个 predict()
                  │     ├─ nodes/plan_generation.py::plan_generation_node
                  │     ├─ nodes/rule_validation.py::rule_validation_node
                  │     │     ├─ domain/scheduling/scheduler.py::Scheduler.schedule
                  │     │     └─ domain/rules/base.py::RuleEngine.hard_violations
                  │     └─ nodes/plan_repair.py::plan_repair_node（有硬违规时循环）
                  └─ plan_service.py::_persist_plan
                      ├─ plan_repository.create / task_repository.create_many
                      ├─ task_standard_repository.create_many
                      └─ session.commit()
          └─ api/v1/mappers.py::plan_read → schemas/plan.py::PlanRead（202 返回）

随后前端订阅：
  GET /api/v1/plans/generation/{job_id}/events
      └─ application/services/generation_service.py::stream_sse（回放 GenerationEvent）
```

---

## 2. `app/` 根与基础层

### `app/__init__.py`
包声明，仅定义 `__version__ = "0.1.0"`（被 `main.py` 的 OpenAPI 与 `/health` 引用）。

### `app/main.py` — **组合根**
| 项 | 说明 |
| --- | --- |
| `lifespan(app)` | 启动时 `core/logging.setup_logging()`；当 `Settings.is_sqlite` 时执行 `infrastructure/database.init_db()`（`create_all`）。**Postgres 不会自动建表，必须走 Alembic** |
| `create_app()` | 构造 FastAPI（title/version/description、`/docs`、`/redoc`、`/openapi.json`）、CORS、注册 `ApplicationError` 全局异常处理器（用 `exc.http_status` + `ErrorResponse`）、挂载 `/health` 与 `api_router` |
| `app` | 模块级实例，供 `uvicorn app.main:app` |
| `run()` | 控制台入口（`pyproject.toml` 的 `damn = "app.main:run"`） |

> 调试入口：`ApplicationError` 的 HTTP 状态全部在这里统一转换，业务层不会直接抛 `HTTPException`。

### `app/core/` — 基础层（禁止 import FastAPI / SQLAlchemy）
| 文件 | 作用 | 关键接口 |
| --- | --- | --- |
| `config.py` | 环境配置唯一来源（pydantic-settings，读 `.env`） | `Settings`（数据库、JWT、LLM、调度默认值）、`get_settings()`（`lru_cache`） |
| `security.py` | 密码哈希 + JWT | `hash_password` / `verify_password`（stdlib PBKDF2-HMAC-SHA256，可换 Argon2）、`create_access_token` / `decode_access_token`、`TokenPayload`、`InvalidTokenError` |
| `logging.py` | 日志初始化 | `setup_logging()`、`get_logger(name)` |

> **易踩坑**：`get_settings()` 有缓存，改了 `.env` 必须重启进程或 `get_settings.cache_clear()`。

---

## 3. 领域层 `app/domain/`

### `domain/models/` — 纯 Pydantic 实体（`from_attributes=True`）
| 文件 | 类 | 作用 |
| --- | --- | --- |
| `base.py` | `DomainModel`、`utcnow()` | 所有实体基类；`from_attributes` 让仓储可直接 `Model.model_validate(orm_row)` |
| `enums.py` | 10 个枚举 | `GoalType` `GoalStatus` `PlanStatus` `TaskStatus` `CognitiveLoad` `Priority(int 1..4)` `ReplanTriggerType` `ViolationSeverity` `TimeOfDay` `LoadLevel` |
| `user.py` | `User` | 账号、`execution_weight`（行动力先验）、`profile` |
| `goal.py` | `Goal` | 目标 + DDL + 优先级 + `options{subject,task_type}` |
| `plan.py` | `Plan` | 计划**版本**（`version`、`parent_plan_id`、`confidence`、`status`） |
| `task.py` | `Task` | 任务：理论时长/预测时长/认知负荷/排期/状态；`order_index`（**临时 id 契约来源**） |
| `task_standard.py` | `TaskStandard` | 可量化完成标准（勾选项） |
| `execution.py` | `TaskExecution` | **ML 数据资产**：计划 vs 实际耗时、完成率、压力前后、难度、失败原因、时间段 |
| `feedback.py` | `Feedback` | 每日反馈：完成率、压力、精力、睡眠、拖延原因 |
| `user_model.py` | `UserModel` | 统计用户模型：`duration_factors` / `completion_probability` / `stress_response` / `preferred_time_slots` / `sample_size` |
| `replan_event.py` | `ReplanEvent` | 重排审计：触发器、原因、旧/新版本、变更任务 |

> 领域模型**不知道**数据库；ORM 镜像在 `infrastructure/database/models/`，由仓储负责双向转换。

### `domain/rules/` — 硬约束引擎（唯一权威）
| 文件 | 内容 | 说明 |
| --- | --- | --- |
| `base.py` | `RuleViolation`、`RuleContext`、`Rule(ABC)`、`RuleEngine`、`default_rules()` | `RuleViolation{rule,severity,task_ids,message,code}`；`RuleEngine.validate/hard_violations/is_valid/register` |
| `cognitive_load.py` | `HighCognitiveNotConsecutiveRule` | 高认知不连续（≥30min 或中间夹非高认知）+ 每日高认知数量上限 |
| `same_day_conflict.py` | `SameDayConflictRule` | 冲突学科（默认 math ↔ algorithm）不得同日 |
| `daily_limit.py` | `DailyLimitRule`、`AvailableTimeRule` | 每日总时长上限；可用时长上限 + 时间窗 |
| `buffer_time.py` | `BufferTimeRule` | 任务间缓冲（重叠也算违规） |
| `deadline.py` | `DeadlineRule` | 不得排到 DDL 之后 |
| `completed_tasks.py` | `CompletedTaskRule` | 已完成任务不得被重新安排 |

> **新增规则必须**在 `default_rules()` 注册，且 `rule.name`、`code` 唯一。

### `domain/scheduling/`
| 文件 | 内容 | 说明 |
| --- | --- | --- |
| `schedule_result.py` | `ScheduledTask`、`CandidateSchedule`、`ScheduleResult` | 排期值对象；`CandidateSchedule` 提供 `tasks_on(day)` / `daily_minutes()` / `days()` |
| `scheduler.py` | `SchedulerConfig`、`Scheduler`、`default_horizon()`、`schedule_tasks()` | 贪心启发式排期，**不调用 LLM**。输入 `list[Task]` + `RuleContext`，输出 `CandidateSchedule` |

> 排期结果只是 candidate，必须再过 `RuleEngine`。

---

## 4. 旁路一：`app/ml/`（预测器接口 + 统计 mock）

| 文件 | 内容 | 说明 |
| --- | --- | --- |
| `base.py` | `TaskFeatureSet`、`UserFeatureSet`、`PredictionRequest`；`DurationPrediction`、`CompletionPrediction`、`StressPrediction`、`TimeSlotPrediction`；4 个 `@runtime_checkable Protocol` | **服务层只依赖这些 Protocol**，不依赖具体实现 |
| `duration_predictor.py` | `StatisticalDurationPredictor` | `predicted = theoretical × factor`（高认知 +15%，难度修正），`source="mock:statistical"` |
| `completion_predictor.py` | `StatisticalCompletionPredictor` | 7d/30d 完成率加权 + 精力/压力/时长惩罚 |
| `stress_predictor.py` | `StatisticalStressPredictor`、`_load_level()` | 平均压力 + 负荷增量；`should_reduce_load` 标记 |
| `time_predictor.py` | `StatisticalTimeSlotPredictor` | 按认知负荷/任务类型查用户偏好时段，兜底默认映射 |
| `user_model.py` | `StatisticalUserModelBuilder`、`_mean()`、`_as_utc()` | `build()` 从历史算 `UserModel`；`to_features()` 产出 `UserFeatureSet` |
| `predictors.py` | `PredictorSet` | 聚合四个预测器；`PredictorSet.default()` 组装统计实现 |

> **不要谎称有训练模型**：v1 全是纯统计。替换真实模型时实现同名 Protocol 并注入 `PlanService(predictors=...)` 即可。

---

## 5. 旁路二：`app/agent/`（LangGraph 编排）

| 文件 | 内容 | 说明 |
| --- | --- | --- |
| `schemas.py` | `AnalyzedGoal`、`GoalAnalysisResult`、`TheoreticalItem`、`TheoreticalAnalysisResult`、`UserSituationResult`、`GeneratedTaskDraft`、`PlanGenerationResult`、`RuleValidationResult`、`PlanRepairResult` | **所有节点输出必须是这里的结构化对象**，禁止把 LLM 自由文本塞进流程 |
| `state.py` | `GoalInput`、`GenerationRequest`、`PlannerState(TypedDict)` | 图的输入契约与状态；`PlannerState` 里包含注入键 `user_features` / `goal_id_map` / `predictors` / `scheduler` / `rule_engine` |
| `graph.py` | `GenerationEvent`、`PlannerGraph`、`build_planner_graph`、`create_planner_graph`、内部 `_LangGraphRunner` / `_SequentialRunner` / `_finalize` / `_synthesize_events` / `_should_repair` | 六个节点的 StateGraph；`langgraph` 不可用时自动降级为顺序执行器 |
| `nodes/__init__.py` | 导出 6 个节点函数 + 5 个 Agent 类 + `build_rule_context` + `drafts_to_tasks` | 图的统一导入面 |
| `nodes/goal_analysis.py` | `GoalAnalysisAgent`、`goal_analysis_node` | 目标 → 目标值 + 子任务 + 约束（mock 启发式） |
| `nodes/theoretical_analysis.py` | `TheoreticalAnalysisAgent`、`theoretical_analysis_node` | 理论工作量：视频/阅读/练习分钟、难度、认知负荷 |
| `nodes/user_situation_analysis.py` | `UserSituationAnalysisAgent`、`user_situation_analysis_node` | 用 4 个预测器算耗时倍率、完成能力、压力、疲劳、推荐时段、是否降载 |
| `nodes/plan_generation.py` | `PlanGenerationAgent`、`drafts_to_tasks()`、`plan_generation_node` | 生成任务草稿；`drafts_to_tasks` 施加**临时 id 契约**并把草稿转成可排期的 `Task` |
| `nodes/rule_validation.py` | `current_drafts()`、`build_rule_context()`、`_parse_time()`、`rule_validation_node` | 排期 + 硬约束校验；从 `user_profile` 读取 `day_start/day_end/conflicting_subject_pairs/completed_task_ids` |
| `nodes/plan_repair.py` | `PlanRepairAgent`、`plan_repair_node` | 有界修复（默认最多丢弃 5 个最低优先级任务），重排后再次校验 |

### `PlannerGraph` 公开接口
```python
PlannerGraph(llm=None, predictors=None, scheduler=None, rule_engine=None, max_repair_attempts=2)

graph.invoke(request, *, user_features, goal_id_map=None) -> PlannerState
graph.run_with_events(request, *, user_features, goal_id_map=None) -> (PlannerState, list[GenerationEvent])
```

### 图结构
```
START → goal_analysis → theoretical_analysis → user_situation_analysis
      → plan_generation → rule_validation
            ├─(有硬违规且 attempts < max)─► plan_repair → rule_validation（循环）
            └─(否则)──────────────────────► END
```

> **调试要点**：`GenerationEvent.stage` 决定 SSE 的 `event:` 名称，必须等于节点名；`run_with_events` 返回的事件顺序也与节点执行顺序一致。

---

## 6. 基础设施层 `app/infrastructure/`

### `database/`
| 文件 | 内容 | 说明 |
| --- | --- | --- |
| `base.py` | `Base(DeclarativeBase)`、`enum_values()` | SQLAlchemy 2.0 声明式基类；`enum_values` 让枚举以 `.value` 存库（跨 SQLite/Postgres 一致） |
| `session.py` | `engine`、`SessionLocal`、`session_scope()`、`init_db()` | SQLite 加 `check_same_thread=False`；`:memory:` 用 `StaticPool`；`expire_on_commit=False` |
| `models/*.py` | 9 个 ORM 类（`User/Goal/Plan/Task/TaskStandard/TaskExecution/Feedback/UserModel/ReplanEvent`） | 表名见下；外键、索引、JSON 列、自引用 FK |
| `repositories/base.py` | `RepositoryBase` | 持有 `session`，只 `flush()`，**绝不 commit** |
| `repositories/*_repository.py` | 9 个仓储 | 返回**领域模型**（`model_validate(orm)`）；`RepositoryBase` 子类 |

表名：`users` `goals` `plans` `tasks` `task_standards` `task_executions` `feedbacks` `user_models` `replan_events`。

各仓储关键方法（服务层直接调用）：
- `UserRepository`: `create` / `get_by_id` / `get_by_email` / `update_fields`
- `GoalRepository`: `create` / `create_many` / `get_by_id` / `list_by_user` / `list_by_ids` / `update_status`
- `PlanRepository`: `create` / `get_by_id` / `list_by_user` / `get_latest_by_user` / `next_version` / `update_status`
- `TaskRepository`: `create_many` / `get_by_id` / `list_by_plan` / `list_by_plan_and_date` / `update_fields` / `delete_by_plan`
- `TaskStandardRepository`: `create_many` / `list_by_task` / `list_by_plan` / `update_fields`
- `TaskExecutionRepository`: `create` / `list_by_user` / `list_by_task`
- `FeedbackRepository`: `create` / `list_by_plan` / `list_by_user` / `get_by_plan_and_date`
- `UserModelRepository`: `get_by_user` / `upsert`
- `ReplanEventRepository`: `create` / `list_by_plan` / `get_latest_for_plan` / **`get_latest_for_user`**（用户级冷却用）

### `llm/`、`ml/`
| 文件 | 内容 | 说明 |
| --- | --- | --- |
| `llm/client.py` | `LLMResponse`、`LLMClient(Protocol)`、`MockLLMClient`、`HttpLLMClient`、`LLMError`、`get_llm_client()` | `complete` 是**同步**的；默认 mock，`LLM_PROVIDER` 切换 |
| `ml/model_store.py` | `ModelStore(Protocol)`、`InMemoryModelStore`、`FileModelStore` | PLACEHOLDER，目前没有可加载的训练模型 |

---

## 7. 应用层 `app/application/`

### `exceptions.py`
`ApplicationError`（带 `code` + `http_status`）及其子类：
`NotFoundError` 404、`PermissionDeniedError` 403、`AuthenticationError` 401、
`ConflictError` 409、`ReplanNotEligibleError` 409、`DomainValidationError` 422。

> `main.py` 统一把这些映射成 `ErrorResponse{code,message,detail}`。

### `dto/` — 服务层返回的内部契约（不是 API schema）
| 文件 | 内容 |
| --- | --- |
| `plan.py` | `PlanDetail`、`TaskWithStandards` |
| `feedback.py` | `FeedbackSubmitResult`（含 `replan_triggered` / `replan_plan_id` / `replan_eligibility`） |
| `replan.py` | `ReplanEligibility`、`ReplanResult`、`ReplanTrigger` |
| `insight.py` | `InsightReport`、`DailyCompletion` |
| `generation.py` | `GenerationJob`、`JobStatus` |

### `services/` — 业务流程编排（事务与权限在这里）
| 文件 | 类 / 关键方法 | 职责 |
| --- | --- | --- |
| `auth_service.py` | `AuthService`：`register` / `authenticate` / `create_token` / `get_user` / `update_user` | 注册、登录、JWT 签发、资料更新；`register` 内 `commit()` |
| `user_model_service.py` | `UserModelService`：`get_model` / `update_model` / `get_user_features` | 从 `TaskExecution` + `Feedback` 重建 `UserModel` 与 `UserFeatureSet` |
| `plan_service.py` | `PlanService`：`generate_plan` / `generate_plan_with_events` / `list_plans` / `get_plan` / `update_task` | **核心编排**：先落 Goal → 组装特征 → 跑图 → 落 Plan/Task/TaskStandard → commit；`update_task(completed=True)` 会写 `TaskExecution` |
| `feedback_service.py` | `FeedbackService`：`submit_feedback` / `list_feedback` | 每日反馈；完成率 `< 0.5` 且可重排时自动触发重排（`AUTO_REPLAN_THRESHOLD`） |
| `replan_service.py` | `ReplanService`：`check_eligibility` / `replan` | 版本化重排：新建 `v(n+1)`、旧版 `superseded`、复制未完成任务并重排、写 `ReplanEvent`；冷却**按用户**（`get_latest_for_user`） |
| `generation_service.py` | `GenerationService`：`create_job` / `get_job` / `stream_sse`、`_sse()` | 进程级内存任务注册表；同步跑完流水线后按序回放 SSE（`event: <stage>`） |
| `insight_service.py` | `InsightService`：`get_insights` | 聚合完成率、计划 vs 实际耗时、压力/精力均值、认知负荷分布、简单建议 |

> **事务归属**：服务在逻辑单元结束时 `commit()`；仓储只 `flush()`。`get_db()` 只负责关闭会话。

---

## 8. 表现层 `app/api/` + `app/schemas/`

### `api/deps.py` — 依赖注入与鉴权
| 依赖 | 作用 |
| --- | --- |
| `get_db()` | 每请求一个 `Session`，结束时关闭（不 commit） |
| `get_auth_service` / `get_user_model_service` / `get_plan_service` / `get_replan_service` / `get_feedback_service` / `get_insight_service` | 服务工厂 |
| `get_generation_service()` | **进程级单例**（内存任务注册表），因此不能持有请求级 session —— `create_job` 每次接收 `plan_service` |
| `get_current_user()` | `HTTPBearer` → `decode_access_token` → `AuthService.get_user`；失败抛 `AuthenticationError` |

### `api/router.py`
聚合各资源路由，统一加前缀 `/api/v1` 与 OpenAPI tags（auth / users / plans / feedback / tasks / insights）。

### `api/v1/`
| 文件 | 端点 | 状态码 |
| --- | --- | --- |
| `auth.py` | `POST /auth/register`、`POST /auth/login` | 201 / 200 |
| `users.py` | `GET /users/me`、`PATCH /users/me` | 200 |
| `plans.py` | `POST /plans/generate`、`GET /plans/generation/{job_id}/events`(SSE)、`GET /plans`、`GET /plans/{plan_id}`、`POST /plans/{plan_id}/replan`、`GET /plans/{plan_id}/replan/eligibility` | 202 / 200 / 200 / 200 / 201 / 200 |
| `feedback.py` | `POST /plans/{plan_id}/feedback`、`GET /plans/{plan_id}/feedback` | 201 / 200 |
| `tasks.py` | `PATCH /plans/{plan_id}/tasks/{task_id}` | 200 |
| `insights.py` | `GET /plans/{plan_id}/insights` | 200 |
| `mappers.py` | `task_read` / `plan_read` / `plan_list_item` / `insight_read` | 领域/DTO → Schema 的唯一映射点 |

> 路由顺序注意：`/plans/generation/{job_id}/events` 定义在 `/plans/{plan_id}` **之前**，否则会被整型路径参数吞掉。

### `schemas/`
| 文件 | 内容 |
| --- | --- |
| `common.py` | `ErrorResponse`、`HealthResponse`、`ViolationRead` |
| `auth.py` | `RegisterRequest`、`LoginRequest`、`TokenResponse` |
| `user.py` | `UserRead`、`UserUpdate` |
| `plan.py` | `GoalCreate`、`GoalRead`、`PlanGenerateRequest`、`PlanGenerateResponse`、`PlanRead`、`PlanListItem`、`ReplanEligibilityRead`、`ReplanRequest`、`ReplanResponse`、`InsightRead`、`GenerationEventRead`、`DailyCompletionRead` |
| `task.py` | `TaskRead`、`TaskStandardRead`、`TaskUpdateRequest`、`TaskStandardUpdate` |
| `feedback.py` | `FeedbackCreate`、`FeedbackRead`、`FeedbackSubmitResponse` |

> 读模型统一 `model_config = ConfigDict(from_attributes=True)`；带嵌套的（Task 的标准、Plan 的任务）由 `mappers.py` 组装。

---

## 9. 必须记住的 5 条不变量

1. **临时任务 id = `order_index + 1`**：图运行时任务尚未落库。`plan_generation.drafts_to_tasks`、
   `rule_validation.build_rule_context`、`plan_repair` 全部用同一规则；`PlanService._persist_plan` 落库后映射成真实 PK。
2. **SSE 事件名 = 节点名**（`goal_analysis` … `plan_repair`）+ 最后 `completed`；由 `GenerationEvent.stage` 生成。
3. **重排冷却按用户**（不是按计划）：`ReplanEventRepository.get_latest_for_user` + `SCHEDULER_MIN_REPLAN_INTERVAL_HOURS`。
4. **一切同步**：service / agent / repository / predictor / `LLMClient.complete` 都是 `def`；只有 SSE 路由是 async。
5. **计划版本不可变**：重排只新增 `v(n+1)`，旧版置 `superseded`，`parent_plan_id` 串联，写 `ReplanEvent`。

---

## 10. 调试清单（按症状定位）

| 症状 | 优先查看 |
| --- | --- |
| 计划没有任务 / 任务全空 | `agent/nodes/plan_generation.py::plan_generation_node` → `agent/graph.py::_finalize` → `PlanService._persist_plan` |
| 任务有 id 但排期为空 | `domain/scheduling/scheduler.py::Scheduler.schedule`；`CandidateSchedule.unscheduled_task_ids` |
| 计划超出每日上限 / 学科冲突仍在同一天 | `domain/rules/*` + `agent/nodes/rule_validation.py::build_rule_context`（检查 `task_subjects` 是否按临时 id 映射） |
| 修复循环不收敛 | `agent/graph.py::_should_repair` 与 `repair_attempts` / `max_repair_attempts`；`nodes/plan_repair.py` |
| SSE 只收到 `completed` | `GenerationEvent.stage` 是否被设为节点名；`generation_service.stream_sse` |
| 重排一直 409 | `ReplanService.check_eligibility`（用户级冷却）→ `replan_events` 表最新记录 |
| 完成率低但没有自动重排 | `FeedbackService.AUTO_REPLAN_THRESHOLD=0.5` 与 eligibility |
| 401 / token 失效 | `core/security.py::decode_access_token`、`api/deps.py::get_current_user`、`JWT_SECRET_KEY` 长度 |
| 测试连错数据库 | `tests/conftest.py` 的 env 必须在 `import app` **之前**设置 |
| Postgres 下表不存在 | 只跑了 `init_db()`（仅 SQLite）；执行 `uv run alembic upgrade head` |
| `WinError 10013` 起不来 | Windows 保留端口，换 8000 |

常用命令：
```bash
uv run pytest tests/unit/test_rules.py -q          # 规则单测
uv run pytest -k scheduler -v                      # 排期相关
uv run pytest tests/integration/test_plan_flow.py -v   # 端到端闭环
uv run uvicorn app.main:app --reload               # 起服务看 /docs
uv run alembic upgrade head                        # 建表 / 迁移
```

---

## 11. 扩展指引（改哪里）

| 需求 | 改这些文件 | 不要动 |
| --- | --- | --- |
| 新增硬约束 | `domain/rules/<new>.py` + 在 `base.py::default_rules()` 注册 | 服务层、API |
| 换真实 LLM | `infrastructure/llm/client.py` 实现 `LLMClient`；`LLM_PROVIDER` 配置 | 节点契约 |
| 换某个 Agent | 改对应 `agent/nodes/<node>.py` 内的 Agent 类 | 图结构与 `PlannerState` |
| 接入真实 ML | `app/ml/` 实现 4 个 Protocol；`PlanService(predictors=...)` 注入；用 `infrastructure/ml/model_store.py` 加载 | service / API / DB |
| 换排期算法 | `domain/scheduling/scheduler.py` 的 `Scheduler.schedule` | 规则、服务 |
| 换数据库 | `infrastructure/database/repositories/*` | 领域层、服务层 |
| 新增 API | `api/v1/<res>.py` + `api/router.py` + `schemas/<res>.py` + `api/v1/mappers.py` | 领域层 |
| 新增字段 | 同时改 `domain/models/<x>.py`、`infrastructure/database/models/<x>.py`、`schemas/<x>.py`、迁移 | 只改一处会漂移 |
