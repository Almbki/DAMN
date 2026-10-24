# 项目结构与真实度盘点（重构准备）

> **STATUS: historical audit (pre-refactor).** This file records the state
> before the three-layer model + Agent refactor. For the current architecture
> see [`model-agent-integration-v1.md`](model-agent-integration-v1.md).
>
> 目的：在重构前，把当前项目的**结构、分层、接口、模块、真实/假数据边界、机器学习模块**一次性盘清。
> 本文只做盘点，不改代码。
>
> 扫描范围：`app/`、`new_frontend/`、`alembic/`、`scripts/`、`tests/`、`docs/`。
> **已排除**：`models_test/`（含 `models_test.zip`）、`node_modules/`、`.venv/`、缓存、`dist/`。
> 当前 Alembic head：`533f463aff00`。

## 状态标签

| 标签 | 含义 |
| --- | --- |
| **REAL** | 真实实现：真实 DB/API/规则/调度/持久化 |
| **REAL+ENG** | 真实逻辑，但参数是工程估计，尚未用数据校准 |
| **MOCK** | 明确的模拟/统计占位，不包含训练模型 |
| **PLACEHOLDER** | 占位实现，没有生产调用方 |
| **OPTIONAL** | 配置后真实可用，否则走确定性回退 |
| **VOLATILE** | 真实逻辑，但状态在进程内存，重启/多 worker 会丢 |
| **DEMO** | 仅演示模式使用，不是生产数据 |
| **UNUSED** | 当前无引用/死代码候选 |

---

# 1. 项目结构（排除 `models_test/`）

```text
DAMN/
├─ app/                         FastAPI 后端
│  ├─ main.py                   组合根：create_app / lifespan / CORS / 健康检查
│  ├─ api/                      表现层：路由、依赖注入、mapper
│  │  ├─ deps.py                会话、service 工厂、JWT 当前用户、GenerationService 单例
│  │  ├─ router.py              聚合 /api/v1 路由
│  │  └─ v1/                    auth/users/goals/plans/tasks/feedback/insights/schedules
│  ├─ schemas/                  Pydantic 请求/响应模型（wire contract）
│  ├─ application/              应用层：编排、事务、DTO、导入
│  │  ├─ services/              auth/plan/generation/feedback/replan/profile/situation/insight/memory/schedule
│  │  ├─ dto/                   服务层内部 DTO
│  │  ├─ context/               RepoContextBuilder：DB → PlanningContext
│  │  ├─ schedule_import.py     CSV/XLSX 解析（扁平表 + 周课表网格）
│  │  ├─ preferences.py         调度/反馈偏好合并
│  │  └─ exceptions.py          框架无关异常
│  ├─ domain/                   领域层：纯逻辑，无 FastAPI/SQLAlchemy
│  │  ├─ models/                实体 + 枚举
│  │  ├─ rules/                 硬约束引擎 + 规则
│  │  ├─ scheduling/            Scheduler + FixedEvent + CandidateSchedule
│  │  ├─ profile/               画像 EWMA 引擎 + MBTI 模板
│  │  └─ feedback/              反馈触发策略（纯函数）
│  ├─ core/                     配置、JWT/密码、日志
│  ├─ infrastructure/           基础设施
│  │  ├─ database/              SQLAlchemy 模型/仓储/session
│  │  ├─ llm/                   LLMClient Protocol + Mock/HTTP 实现
│  │  └─ ml/model_store.py      模型产物存储（占位）
│  ├─ agent/                    LangGraph 旁路
│  │  ├─ graph.py               两张图 + PlannerGraph 门面
│  │  ├─ router.py              条件边 + AdjustmentRouter
│  │  ├─ state.py               PlannerState/PlannerContext/PlannerRequest
│  │  ├─ nodes/                 15 个图节点 + _shared
│  │  ├─ tools/                 7 个工具
│  │  ├─ prompts/               6 个 prompt 模板
│  │  ├─ memory/                semantic/episodic/procedural
│  │  └─ checkpointer.py        Postgres / InMemory checkpointer
│  └─ ml/                       预测器旁路
│     ├─ base.py                Protocols + 请求/响应契约
│     ├─ predictors.py          PredictorSet.default()
│     ├─ duration_predictor.py  统计 mock
│     ├─ completion_predictor.py统计 mock
│     ├─ stress_predictor.py    统计 mock
│     ├─ time_predictor.py      统计 mock
│     └─ adjustment.py          规则回退 + 测试 mock
├─ alembic/                     迁移；env.py 读 Settings
├─ scripts/evaluate_predictors.py  预测评分脚本（评估 mock 预测）
├─ tests/                       pytest（unit/api/agent/integration）
├─ docs/                        设计与盘点文档
├─ new_frontend/                Expo / React Native (SDK 57)
│  ├─ src/app/                  expo-router 页面
│  ├─ src/components/           UI 组件
│  ├─ src/state/                Context/Provider
│  ├─ src/api/                  client/endpoints/types/mapper
│  ├─ src/domain/               纯前端领域函数
│  ├─ src/data/mock.ts          DEMO 假数据
│  ├─ src/notifications/        本地反馈提醒
│  └─ src/constants/            tokens/nav
├─ ideas and structures/        原始设计笔记（参考，不运行）
├─ test.xlsx                    用户课程表样例（解析用）
├─ pyproject.toml / uv.lock
├─ alembic.ini / .env
├─ Dockerfile / docker-compose.yml
├─ README.md / AGENTS.md
└─ models_test/                 **已排除**（models_test.zip）
```

---

# 2. 系统分层

## 2.1 后端分层

```text
前端 HTTP / SSE
      │
      ▼
┌──────────────────────────────────────────────┐
│ 表现层 API/Presentation                      │
│ app/api/**、app/schemas/**、app/main.py      │
│ 路由、鉴权、校验、HTTP 状态、OpenAPI、mapper  │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│ 应用层 Application                           │
│ app/application/**                           │
│ 事务、权限、编排、DTO、导入、上下文构建       │
└───────┬──────────────────────────┬───────────┘
        │ 旁路调用                  │
        ▼                          ▼
┌──────────────────┐     ┌──────────────────────┐
│ app/agent/**      │     │ app/ml/**            │
│ LangGraph 状态机  │     │ 预测器 Protocol+mock │
└───────┬──────────┘     └──────────┬───────────┘
        │                           │
        ▼                           ▼
┌──────────────────────────────────────────────┐
│ 领域层 Domain + 基础层 Core                  │
│ app/domain/**（实体/规则/调度/画像/反馈策略） │
│ app/core/**（配置/JWT/日志）                 │
│ 纯逻辑，不 import FastAPI/SQLAlchemy          │
└──────────────────▲───────────────────────────┘
                   │ 基础设施依赖领域
┌──────────────────┴───────────────────────────┐
│ 基础设施 Infrastructure                      │
│ app/infrastructure/**                        │
│ SQLAlchemy 模型/仓储/session、LLM、model store│
└──────────────────────────────────────────────┘
```

关键规则（当前代码基本遵守）：

- `app/core`、`app/domain` 不 import FastAPI / SQLAlchemy。
- Agent 不碰 DB；由 `PlanService` 通过 `PlannerContext`/`PlanningContext` 注入。
- 仓储只 `flush()`，不 `commit()`；Service 拥有事务。
- `RuleEngine` 是硬约束唯一权威；Scheduler 不调用 LLM。
- API 不直接返回 ORM/领域对象；经 `api/v1/mappers.py` 映射。

## 2.2 前端分层

```text
app/ (expo-router 页面)
  index / goal / feedback / profile / profile-details / settings / +not-found
        │
        ▼
components/ (任务、课程表、反馈、画像、Shell、UI 基础组件)
        │
        ▼
state/ (Context/Provider)
  api-plan (真实 API) / plan (mock DEMO) / schedule / profile / session /
  preferences-store / theme / plan-context
        │
        ▼
api/ (client: JSON/SSE/multipart；endpoints；types；mapper；config)
        │
        ▼
FastAPI /api/v1
```

- `dataSource` 默认 `api`；只有显式 `EXPO_PUBLIC_DATA_SOURCE=mock` 才走 DEMO。
- Mock 分支：`MockPlanProvider` + `src/data/mock.ts` + 本地 `domain/decompose.ts`/`situation.ts`/`insight.ts`。
- API 分支：`SessionProvider` + `ApiPlanProvider`，JWT 存 `localStorage`（Web）或内存（原生）。
- 课程表 `ScheduleProvider` **只走 API**；mock 模式下没有课程表数据。
- 反馈提醒：原生 `expo-notifications` 真实本地通知；Web 不支持，用 App 内阻断提示。

## 2.3 核心数据流

1. **生成/拆解**：API 202 job → `GenerationService` 后台线程 → `PlanService` → LangGraph A → Scheduler → RuleEngine → 落库 → SSE。
2. **预览/确认**：Graph A 在 `preview` interrupt；confirm resume 后落 Plan/Task/TaskStandard。
3. **执行**：`PATCH task` 更新状态/实际数据；完成时写 `task_executions`；更新画像 EWMA。
4. **反馈**：反馈落库 → 画像更新 → 反馈策略（压力/精力 + 画像）→ 可选 Graph B → 新版本/不重排。
5. **重排**：手动冷却检查 → Graph B → 新 Plan 版本 + ReplanEvent。
6. **课程表**：上传 CSV/XLSX → `schedule_import` 解析 → `schedule_events` → RepoContextBuilder 展开为固定事件 → Scheduler/RuleEngine 避让。
7. **反馈提醒**：用户偏好时间 → 原生本地通知 + App 内 gate。

---

# 3. 接口清单

前缀：`/api/v1`。除 `auth/register`、`auth/login`、`/health`、`/docs` 外，均需 Bearer JWT。

## 3.1 Auth

| 方法 | 路径 | 状态码 | 说明 | 真实度 |
| --- | --- | --- | --- | --- |
| POST | `/auth/register` | 201 | 注册；可选初始化画像 | REAL |
| POST | `/auth/login` | 200 | 登录 → JWT | REAL |

## 3.2 Users / Profile / Preferences

| 方法 | 路径 | 状态码 | 说明 | 真实度 |
| --- | --- | --- | --- | --- |
| GET | `/users/me` | 200 | 当前用户 | REAL |
| PATCH | `/users/me` | 200 | 改资料/画像字段 | REAL |
| GET | `/users/me/profile` | 200/404 | 静态画像 + EWMA 状态 | REAL+ENG（画像系数） |
| GET | `/users/me/preferences` | 200 | 调度/反馈偏好 | REAL |
| PUT | `/users/me/preferences` | 200 | 覆盖偏好（含 feedback_time/enabled） | REAL |
| GET | `/users/me/situation/trends?days=2..90` | 200 | 精力/压力/效能趋势 | REAL（基于反馈/执行） |

## 3.3 Goals

| 方法 | 路径 | 状态码 | 说明 | 真实度 |
| --- | --- | --- | --- | --- |
| GET | `/goals?status=` | 200 | 目标列表（draft=待拆解） | REAL |
| POST | `/goals` | 201 | 创建目标/草稿 | REAL |
| PATCH | `/goals/{goal_id}` | 200 | 编辑目标 | REAL |
| DELETE | `/goals/{goal_id}` | 204/409 | 删除；仍被任务引用则 409 | REAL |

## 3.4 Plans（生成 / 预览 / 确认 / 拆解 / 重排）

| 方法 | 路径 | 状态码 | 说明 | 真实度 |
| --- | --- | --- | --- | --- |
| POST | `/plans/generate` | 202 | 异步生成 job；结果在 job | REAL（ML 预测为 MOCK） |
| POST | `/plans/preview` | 202 | 异步预览 job，停在 confirm | REAL |
| POST | `/plans/preview/{thread_id}/confirm` | 201 | 确认预览 → Plan v1 | REAL |
| POST | `/plans/preview/{thread_id}/adjust` | 202 | 有界调整 job | REAL |
| POST | `/plans/decompose` | 202 | 前端拆解契约；返回按天草稿 | REAL |
| POST | `/plans/confirm` | 200 | 确认草稿 → 正式计划 | REAL |
| GET | `/plans/generation/{job_id}` | 200 | job 状态/结果/事件 | REAL（内存 job） |
| GET | `/plans/generation/{job_id}/events` | 200 | SSE 实时事件 | REAL |
| GET | `/plans` | 200 | 计划列表 | REAL |
| GET | `/plans/{plan_id}` | 200 | 计划详情（任务/标准/目标） | REAL |
| GET | `/plans/{plan_id}/changes` | 200 | 重排按天 diff | REAL |
| POST | `/plans/{plan_id}/replan` | 202/409 | 手动重排（用户级冷却） | REAL |
| GET | `/plans/{plan_id}/replan/eligibility` | 200 | 重排资格 | REAL |

## 3.5 Tasks

| 方法 | 路径 | 状态码 | 说明 | 真实度 |
| --- | --- | --- | --- | --- |
| PATCH | `/plans/{plan_id}/tasks/{task_id}` | 200 | 改状态/实际数据/标准/标题/时长/优先级/日期时间 | REAL |
| DELETE | `/plans/{plan_id}/tasks/{task_id}` | 204 | 软删除任务（保留执行/标准） | REAL |

## 3.6 Feedback

| 方法 | 路径 | 状态码 | 说明 | 真实度 |
| --- | --- | --- | --- | --- |
| POST | `/plans/{plan_id}/feedback?stream_replan=true` | 201 | 落库反馈；可选异步重排 job；支持 `task_reasons` | REAL（重排策略 REAL+ENG；ML 信号 MOCK） |
| GET | `/plans/{plan_id}/feedback` | 200 | 反馈历史 | REAL |

## 3.7 Insights

| 方法 | 路径 | 状态码 | 说明 | 真实度 |
| --- | --- | --- | --- | --- |
| GET | `/plans/{plan_id}/insights` | 200 | 完成率/实际耗时/压力/建议 | REAL |

## 3.8 Schedules（课程表）

| 方法 | 路径 | 状态码 | 说明 | 真实度 |
| --- | --- | --- | --- | --- |
| POST | `/schedules/import` | 200 | multipart CSV/XLSX；支持 `dry_run`、`term_start`；返回 counts/warnings/conflicts | REAL |
| GET | `/schedules?from=&to=` | 200 | 列出窗口内事件（含每周重复） | REAL |
| DELETE | `/schedules/{event_id}` | 204/404 | 删除事件（重复课程整系列） | REAL |

## 3.9 System

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查 |
| GET | `/docs`、`/redoc`、`/openapi.json` | FastAPI 文档 |

> 注意：`POST /plans/generate`、`/preview`、`/adjust`、`/decompose`、`/replan` 都是 **202 + job**；只有两个 `confirm` 是同步落库。

---

# 4. 后端模块清单

## 4.1 表现层 `app/api` + `app/schemas`

| 文件 | 职责 | 真实度 |
| --- | --- | --- |
| `app/main.py` | 组合根、lifespan、CORS、异常映射、/health | REAL |
| `app/api/deps.py` | DB session、service 工厂、JWT、GenerationService 单例 | REAL |
| `app/api/router.py` | 聚合 8 组路由 | REAL |
| `app/api/v1/auth.py` | 注册/登录 | REAL |
| `app/api/v1/users.py` | me/profile/preferences/trends | REAL |
| `app/api/v1/goals.py` | 目标 CRUD | REAL |
| `app/api/v1/plans.py` | 生成/预览/确认/调整/拆解/列表/详情/变更/重排/job/SSE | REAL |
| `app/api/v1/tasks.py` | 任务 PATCH/DELETE | REAL |
| `app/api/v1/feedback.py` | 反馈提交/历史 | REAL |
| `app/api/v1/insights.py` | 洞察 | REAL |
| `app/api/v1/schedules.py` | 课程表导入/列表/删除 | REAL |
| `app/api/v1/mappers.py` | 领域/DTO → Schema 唯一映射点 | REAL |
| `app/schemas/**` | 请求/响应模型 | REAL |

## 4.2 应用层 `app/application`

| 文件 | 职责 | 真实度 |
| --- | --- | --- |
| `services/plan_service.py` | 核心编排：生成/预览/确认/调整/重排/落库/更新任务 | REAL |
| `services/generation_service.py` | 后台 job + SSE；进程内注册表 | REAL / VOLATILE |
| `services/feedback_service.py` | 反馈落库、画像更新、触发策略 | REAL |
| `services/replan_service.py` | 用户级重排冷却资格 | REAL |
| `services/profile_service.py` | 画像持久化、EWMA、features、replan 决策 | REAL+ENG |
| `services/situation_service.py` | 精力/压力/效能趋势 | REAL |
| `services/insight_service.py` | 计划分析/建议 | REAL |
| `services/memory_service.py` | 记忆刷新（best-effort） | REAL |
| `services/schedule_event_service.py` | 课程表导入/列表/删除 | REAL |
| `services/auth_service.py` | 注册/登录/JWT/资料/偏好 | REAL |
| `services/goal_service.py` | 目标 CRUD/归属/引用检查 | REAL |
| `context/repo_context_builder.py` | DB → PlanningContext（唯一通道） | REAL |
| `schedule_import.py` | CSV/XLSX 解析（扁平 + 周网格 + teacher/周次） | REAL |
| `preferences.py` | 偏好默认/合并 | REAL |
| `dto/**` | 服务内部 DTO | REAL |
| `exceptions.py` | 框架无关异常 | REAL |

## 4.3 领域层 `app/domain`

| 目录/文件 | 职责 | 真实度 |
| --- | --- | --- |
| `models/**` | 实体/枚举（User/Goal/Plan/Task/TaskStandard/TaskExecution/Feedback/ReplanEvent/AgentRun/AgentMemory/PredictionLog/ScheduleEvent） | REAL |
| `rules/base.py` | RuleEngine/Context/Violation/default_rules | REAL |
| `rules/*.py` | 9 条硬约束：认知负荷、学科冲突、每日上限、可用时间、缓冲、DDL、已完成、最早开始、固定日程冲突 | REAL |
| `scheduling/scheduler.py` | 贪心确定性排期（含 fixed events/earliest） | REAL |
| `scheduling/fixed_events.py` | 固定日程展开/重叠 | REAL |
| `scheduling/schedule_result.py` | CandidateSchedule/ScheduledTask/FixedEvent | REAL |
| `profile/engine.py` | 画像 EWMA/决策/预测公式（纯函数） | REAL+ENG |
| `profile/mbti_templates.py` | MBTI 先验表 | REAL+ENG（工程估计） |
| `profile/models.py` | 画像数据类 | REAL |
| `feedback/policy.py` | 反馈触发重排策略（压力/精力 + 画像） | REAL+ENG（阈值可配） |

## 4.4 基础层 `app/core`

| 文件 | 职责 | 真实度 |
| --- | --- | --- |
| `config.py` | Settings（`.env` 绝对路径） | REAL |
| `security.py` | PBKDF2 + JWT | REAL |
| `logging.py` | 日志初始化 | REAL |

## 4.5 基础设施 `app/infrastructure`

| 目录/文件 | 职责 | 真实度 |
| --- | --- | --- |
| `database/session.py` | engine/SessionLocal/session_scope/init_db | REAL |
| `database/models/**` | SQLAlchemy ORM（含 user_state/schedule_event） | REAL |
| `database/repositories/**` | 13+ 仓储，只 flush | REAL |
| `llm/client.py` | LLMClient Protocol、MockLLMClient、HttpLLMClient | REAL（HTTP）/ MOCK（Mock） |
| `ml/model_store.py` | 模型产物存储 Protocol + 内存/文件实现 | PLACEHOLDER / UNUSED |

## 4.6 Agent 旁路 `app/agent`

| 目录/文件 | 职责 | 真实度 |
| --- | --- | --- |
| `graph.py` | Graph A/B + PlannerGraph 门面 | REAL |
| `state.py` | PlannerState/Context/Request/AgentConfig | REAL |
| `context.py` | PlanningContext/CurrentPlanSnapshot | REAL |
| `router.py` | 条件边 + AdjustmentRouter + ClassifyPolicy | REAL |
| `nodes/**` | 15 个节点 + `_shared`；多数确定性启发式 | REAL（启发式）/ OPTIONAL（LLM） |
| `tools/**` | 7 个工具 | REAL（启发式）/ OPTIONAL（LLM） |
| `prompts/*.md` | 6 个 prompt 模板 | REAL |
| `memory/**` | semantic/episodic/procedural 纯函数 | REAL |
| `checkpointer.py` | PostgresSaver / InMemorySaver | REAL（PG）/ VOLATILE（SQLite） |

## 4.7 ML 旁路 `app/ml`

| 文件 | 职责 | 真实度 |
| --- | --- | --- |
| `base.py` | 4 个 Predictor Protocol + 请求/响应契约 | REAL（接口） |
| `predictors.py` | PredictorSet.default() 组装 | REAL（装配） |
| `duration_predictor.py` | 统计时长预测 | MOCK（`source="mock:statistical"`） |
| `completion_predictor.py` | 统计完成率预测 | MOCK |
| `stress_predictor.py` | 统计压力预测 | MOCK |
| `time_predictor.py` | 统计时段预测 | MOCK |
| `adjustment.py` | 规则回退 + 测试 double | MOCK/回退（`source="fallback:rule"`） |

## 4.8 脚本 / 迁移

| 文件 | 职责 | 真实度 |
| --- | --- | --- |
| `scripts/evaluate_predictors.py` | 用 `prediction_logs` 评分预测 | REAL（评的是 mock 预测） |
| `alembic/versions/**` | 迁移链 | REAL |

---

# 5. 前端模块清单

## 5.1 页面 `src/app`

| 页面 | 路径 | 功能 | 真实度 |
| --- | --- | --- | --- |
| `index.tsx` | `/` | 今日/本周/每月待办、任务操作、反馈入口、课程表 section | REAL（API 模式） |
| `goal.tsx` | `/goal` | 待拆解、拆解预览、确认 | REAL（API 模式） |
| `feedback.tsx` | `/feedback` | 自动完成清单、未完成原因、精力/压力滑条、历史 | REAL（API 模式） |
| `profile.tsx` | `/profile` | 画像、趋势、状态 | REAL（API 模式） |
| `profile-details.tsx` | `/profile-details` | 基础档案、睡眠/可用时间、反馈提醒 | REAL（API 模式） |
| `settings.tsx` | `/settings` | 排程偏好、执行权重 | REAL（API 模式） |
| `+not-found.tsx` | — | 404 | REAL |
| `_layout.tsx` | — | Provider、FeedbackGate、全局错误 | REAL |

## 5.2 状态 `src/state`

| 文件 | 职责 | 真实度 |
| --- | --- | --- |
| `api-plan.tsx` | API 模式核心 store：计划/任务/反馈/偏好/重排/删除/编辑 | REAL |
| `plan.tsx` | Provider 工厂 + MockPlanProvider | DEMO（mock 分支） |
| `plan-context.ts` | Context 类型 | REAL |
| `schedule.tsx` | 课程表状态：拉取/导入/删除/周切换 | REAL（仅 API） |
| `profile.tsx` | 画像 API/mock provider | REAL / DEMO |
| `session.tsx` | 自动登录/JWT/session | REAL |
| `preferences-store.ts` | 偏好缓存/远端 PUT | REAL |
| `theme.tsx` | 主题（当前 light） | REAL |
| `profile-context.ts` | 画像 Context 类型 | REAL |

## 5.3 API 层 `src/api`

| 文件 | 职责 | 真实度 |
| --- | --- | --- |
| `client.ts` | JSON 请求、SSE、multipart 上传、错误 envelope、401 | REAL |
| `config.ts` | dataSource/API base URL/超时 | REAL |
| `endpoints.ts` | 所有后端端点封装 | REAL |
| `types.ts` | wire 类型 | REAL |
| `mapper.ts` | wire → 前端领域模型 | REAL |
| `format.ts` | 时间格式化 | REAL |

## 5.4 领域 `src/domain`

| 文件 | 职责 | 真实度 |
| --- | --- | --- |
| `task.ts` | Task/TaskKind/TaskStandard 类型与标签 | REAL |
| `task-ops.ts` | 本地状态迁移（mock 用） | DEMO（mock 分支） |
| `stats.ts` | 今日完成率/统计 | REAL |
| `selectors.ts` | smart lists/周日期 | REAL |
| `goal.ts` | Goal 类型 | REAL |
| `decompose.ts` | 本地拆解（mock） | DEMO |
| `situation.ts` | 本地趋势公式（mock） | DEMO |
| `insight.ts` | 本地洞察（mock） | DEMO |
| `mbti.ts` | MBTI 映射 | REAL |
| `quick-add.ts` | 自然语言快速添加（mock quick-add） | DEMO |
| `date.ts` | 本地日期工具 | REAL |
| `preferences.ts` | 偏好默认/归一化 | REAL |
| `plan-change.ts` | 变更类型 | REAL |

## 5.5 组件

| 目录 | 内容 | 真实度 |
| --- | --- | --- |
| `components/task/**` | TaskDetailSheet、TaskAddDialog、TaskKindBadge、WeekdayPicker、ScaleSlider、Banner 等 | REAL |
| `components/schedule/**` | 30 分钟课程表、当前时间线、导入/详情/删除 | REAL |
| `components/feedback/**` | 反馈页组件、FeedbackGate、原因卡片、历史、提醒开关 | REAL |
| `components/profile/**` | MBTI、维度滑条、状态仪表盘 | REAL |
| `components/shell/**` | AppShell/5 tab 导航 | REAL |
| `components/ui/**` | Button/Dialog/BottomSheet/Segmented/DatePicker 等 | REAL |
| `timeline.tsx`、`task-row.tsx`、`task-meta.tsx` | 待办时间轴/列表 | REAL |
| `trend-chart.tsx` | 趋势图 | REAL |
| `plan-change-sheet.tsx` | 重排变更 | REAL |
| `decompose-preview-dialog.tsx` | 拆解预览 | REAL |
| `data/mock.ts` | DEMO 假数据（任务/目标/画像/反馈） | DEMO |
| `notifications/feedback-reminder.ts` | 本地通知调度 | REAL（原生）/ 不支持（Web） |

---

# 6. 用户功能 × 真实/假数据对照

| 用户功能 | 前端入口 | 后端链路 | 数据来源 | 真实度 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 注册/登录 | 自动登录/接口 | AuthService + UserRepository + JWT | `users` | REAL | 无独立登录页；demo 账号自动登录 |
| 资料/画像/偏好 | `/profile`、`/profile-details`、`/settings` | ProfileService/AuthService | `users`、`user_states`、preferences JSON | REAL+ENG | EWMA 真实更新；MBTI/系数是工程估计 |
| 趋势 | `/profile` | SituationService | `feedbacks`、`task_executions` | REAL | 数据少时显示不足 |
| 目标 CRUD | `/goal` | GoalService + GoalRepository | `goals` | REAL | — |
| 拆解/预览/确认 | `/goal` | PlanService + LangGraph A + Scheduler + RuleEngine | `goals`、`plans`、`tasks`、`task_standards`、checkpoint | REAL（管线）/ MOCK（ML 预测）/ OPTIONAL（LLM） | 结果依赖 LLM 是否配置成功 |
| 生成计划 | `/goal`/API | PlanService + Graph A | 同上 + `prediction_logs` | REAL / MOCK ML | — |
| 调整预览 | `/goal` | PlanService + Graph A resume | 同上 | REAL | 预算限制 |
| 计划列表/详情/变更 | `/`、`/plan-change-sheet` | PlanService/ReplanEventRepository | `plans`、`tasks`、`replan_events` | REAL | `changed_task_ids` 仍返回全部任务（已知） |
| 手动重排 | `/` | ReplanService + PlanService + Graph B | `replan_events`、新 plan/tasks | REAL | 用户级冷却 |
| 任务编辑/改期 | TaskDetailSheet | PlanService.update_task | `tasks` | REAL | 不重新跑 RuleEngine（手动覆盖） |
| 删除任务 | TaskDetailSheet | PlanService.delete_task | `tasks.deleted_at` | REAL | 软删除，保留 execution/standard |
| 每日反馈 | `/feedback` | FeedbackService + Policy + Graph B | `feedbacks.task_reasons`、`user_states` | REAL（落库/策略）/ MOCK（ML 信号） | `task_reasons` 暂未参与策略 |
| 反馈提醒 | `/profile-details` + gate | preferences + expo-notifications | `users.scheduling_preferences` | REAL（原生）/ Web 不支持 | App 内阻断 + 15 分钟 snooze×2 |
| 洞察 | `/`/profile | InsightService | `tasks`、`task_executions`、`feedbacks` | REAL | 数据稀疏时提示不足 |
| 课程表导入/展示 | `/` ScheduleSection | ScheduleEventService + parser + Scheduler/RuleEngine | `schedule_events` | REAL | `test.xlsx` 解析 46 条；原始文件不保存 |
| 长期任务 | `/goal` 新建 | PlanDrafter 按天拆分 + Scheduler earliest | `goals`、`tasks`(series_id/occurrence) | REAL | 确定性拆分；series 编辑/删除仍按单条 |
| 异步 job/SSE | `/`/goal | GenerationService | 进程内存 | REAL / VOLATILE | 多 worker 需 sticky/Redis |
| DEMO 模式 | 全局 | MockPlanProvider + mock.ts | 前端假数据 | DEMO | 仅 `EXPO_PUBLIC_DATA_SOURCE=mock` |

---

# 7. 机器学习模块专项（重构重点）

## 7.1 结论

**当前没有任何训练好的 ML 模型。** `app/ml/**` 是“统计/规则 mock”，用于把接口和链路跑通；`infrastructure/ml/model_store.py` 是占位，且当前没有调用方。

## 7.2 模块清单

| 模块 | 角色 | 当前实现 | 状态 | 重构建议 |
| --- | --- | --- | --- | --- |
| `app/ml/base.py` | 预测器接口 | `Duration/Completion/Stress/TimeSlot/Adjustment` Protocols + 请求/响应模型 | REAL（契约） | 保留为唯一替换缝 |
| `app/ml/predictors.py` | 装配 | `PredictorSet.default()` 接统计 mock | REAL（装配） | 增加配置/DI，避免硬编码 |
| `app/ml/duration_predictor.py` | 时长预测 | 理论分钟 × factor + 认知/难度修正 | MOCK | 替换为训练模型 |
| `app/ml/completion_predictor.py` | 完成率预测 | 7d/30d 完成率 + 惩罚 | MOCK | 替换为训练模型 |
| `app/ml/stress_predictor.py` | 压力预测 | 平均压力 + 负荷增量 | MOCK | 替换为训练模型 |
| `app/ml/time_predictor.py` | 时段预测 | 偏好/静态默认 | MOCK | 替换为训练模型 |
| `app/ml/adjustment.py` | 重排路由预测 | 规则阈值；`MockAdjustmentPredictor` 测试 | MOCK/回退 | 未来可换 GBDT/校准模型 |
| `app/domain/profile/engine.py` | 画像 EWMA/决策 | 真实数学；系数为工程值 | REAL+ENG | 用真实执行数据校准 |
| `app/domain/profile/mbti_templates.py` | MBTI 先验 | 16 型 + default 工程表 | REAL+ENG | 保留为冷启动先验，标注来源 |
| `app/infrastructure/ml/model_store.py` | 模型产物存储 | InMemory/File（pickle） | PLACEHOLDER / UNUSED | 接对象存储/MLflow；当前无调用 |
| `scripts/evaluate_predictors.py` | 离线评分 | 读 `prediction_logs` 评估 | REAL（评 mock） | 训练/上线前评估门槛 |
| `prediction_logs` | 预测数据资产 | 每次预测写入 | REAL | 未来训练/校准数据源 |
| `task_executions` | 执行数据资产 | 计划 vs 实际/压力/失败原因 | REAL | 主要训练数据 |
| `feedbacks` | 反馈数据 | 完成率/压力/精力/原因 | REAL | 画像/策略训练 |
| `agent_runs` | Agent 审计 | 事件/trace | REAL | 可观测性 |
| `agent_memories` | 记忆 | semantic/episodic/procedural | REAL | 可做 RAG 数据源 |

## 7.3 LLM 与 ML 的区别

- **LLM**：`app/agent/llm.py::StructuredLLM` + `infrastructure/llm/client.py`。
  - `HttpLLMClient` 是真实 OpenAI 兼容 HTTP；`.env` 当前 `LLM_PROVIDER=openai_compatible`、`LLM_MODEL=deepseek-flash`。
  - `MockLLMClient` 是 mock；代码默认 `llm_provider="mock"`，但 `.env` 覆盖为 HTTP。
  - 失败会重试并回退到确定性结果；`source` 会标记 `llm` / `fallback:*`。
- **ML**：`app/ml/**` 是数值预测；当前全部是统计/规则 mock，与 LLM 无关。
- **画像**：`app/domain/profile/**` 是规则/EWMA 模型，不是训练模型，也不依赖 LLM。

## 7.4 接入真实 ML 的最小路径

1. 实现 `DurationPredictor` / `CompletionPredictor` / `StressPredictor` / `TimeSlotPredictor` 四个 Protocol。
2. 在 `PredictorSet` 注入实现；`PlanService` 不需要改。
3. 用 `model_store` 加载产物；补真实 artifact store。
4. 用 `prediction_logs` + `task_executions` 训练/校准；`scripts/evaluate_predictors.py` 做门槛。
5. 前端继续只读 `prediction_source`/`completion_probability`，不需要改契约。

---

# 8. 运行时与存储

## 8.1 数据库表

| 表 | 内容 | 真实度 |
| --- | --- | --- |
| `users` | 账号、画像静态列、偏好 JSON | REAL |
| `user_states` | 画像 EWMA 状态 | REAL |
| `goals` | 目标/长期定义 | REAL |
| `plans` | 计划版本（不可变） | REAL |
| `tasks` | 任务/长期 occurrence/软删除 | REAL |
| `task_standards` | 完成标准 | REAL |
| `task_executions` | ML 数据资产 | REAL |
| `feedbacks` | 每日反馈 + `task_reasons` | REAL |
| `replan_events` | 重排审计 | REAL |
| `agent_runs` | Agent trace | REAL |
| `agent_memories` | 记忆 | REAL |
| `prediction_logs` | 预测日志 | REAL |
| `schedule_events` | 课程表/固定日程（含 teacher） | REAL |
| LangGraph checkpoint 表 | checkpoint/blobs/writes | REAL（Postgres）/ 内存（SQLite） |

## 8.2 进程内状态（VOLATILE）

- `GenerationService` job 注册表：内存；重启丢失；多 worker 不共享。
- `get_llm_client` 缓存：进程内；配置变更需重启。
- `get_settings` lru_cache：改 `.env` 需重启。
- `PlannerContext.tools` 缓存：每次运行懒构建。
- SQLite 下 checkpointer = InMemorySaver；Postgres 下 = PostgresSaver。

## 8.3 外部依赖

- LLM：DeepSeek/OpenAI 兼容 HTTP（可关）。
- 原生通知：`expo-notifications`（Web 不支持）。
- 无外部 ML 服务；无向量数据库；无 RAG。

---

# 9. 重构关注点与已知风险

## 9.1 真实/假数据边界

1. **ML 全部是 mock**：不要把 `app/ml/*` 当训练模型；`model_store` 是占位。
2. **LLM 是可选真实**：`.env` 配了 DeepSeek，但失败会回退；必须看 `source`/`used_llm`。
3. **前端 mock 模式是 DEMO**：`dataSource=mock` 时所有“真实 API”链路都不是真的。
4. **课程表/反馈/new 任务是真实持久化**：不要再误认为前端本地存储。

## 9.2 架构债

- 应用层反向依赖 API schema（`goal_service`/`situation_service` 等）。
- API 层构造 ORM `Feedback`（`api/v1/feedback.py`）。
- `application/dto/plan.py` 内嵌 ORM 实体。
- `DEFAULT_HORIZON_DAYS` 三处不一致（plans/plan_service=13，scheduler=14）。
- `changed_task_ids` 返回新版本全部任务（已知 TODO）。
- `plan_service.py` 的 `get_plan(user_id, 0)` 潜在分支 bug。
- `PATCH task` 的 execution-only 字段在 `completed=false` 时可能被静默丢弃。
- Scheduler 预检与 RuleEngine 策略重复（维护双份）。
- 课程表：无手动新增/编辑单条事件；重复课程删除整系列；周次按多条事件存储。
- 反馈：`task_reasons` 只落库，尚未参与策略；FeedbackGate 用本地 `lastFeedbackDate` + 当前计划历史。
- 前端 mock/api 双 Provider 并存；`plan.tsx` 与 `api-plan.tsx` 需长期同步。
- `task-editor.tsx` 当前无引用（死代码候选）。
- `model_store.py` 无调用方（占位）。
- `classify_request` 节点写 `classify` 但无人读取（语义孤儿）。
- `new_plan` 节点复用 `plan_finalization`，SSE/审计里看不到 `new_plan`。

## 9.3 重构优先级建议

1. **先隔离 ML 边界**：把 `app/ml/**` 标注为可替换 sidecar；真实模型只通过 Protocol 接入。
2. **把 mock/真实数据边界写进 UI**：所有预测显示 `source`/`degraded`；mock 模式加全局标识。
3. **拆掉应用层对 API schema 的反向依赖**；API 不构造 ORM。
4. **统一 horizon/常量；修已知 latent bug**。
5. **把 job 注册表/checkpointer 从内存改为共享存储**（Redis/Postgres）。
6. **前端收敛双 Provider**：API 为主，mock 作为独立 demo 包。
7. **课程表补手动 CRUD/单次例外**；反馈原因接入策略/训练。

---

# 10. 运行与验证

```bash
# 后端
uv sync
uv run alembic upgrade head
uv run pytest
uv run ruff check .
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd new_frontend
npm install
npm run typecheck
npm run lint
npx expo start --clear
```

- SQLite dev 默认：`DATABASE_URL=sqlite:///./dev.db`；Postgres 走 Alembic。
- `.env` 现在从项目根目录绝对读取；改了 `.env` 需重启。
- Web 生产构建：`npx expo export --platform web`。

---

# 11. 快速结论

- **真实可用**：认证、目标、计划生成/预览/确认/调整/重排、任务编辑/删除、反馈落库与提醒、洞察、课程表导入/避让、长期任务拆分、SSE/job。
- **真实但未校准**：画像 EWMA、反馈触发阈值、MBTI 先验。
- **假数据/占位**：`app/ml/*` 四个统计预测器、`adjustment` 规则回退、`model_store`、前端 `mock` 分支。
- **可选真实**：LLM（DeepSeek/OpenAI 兼容，失败回退）。
- **易被误判**：`test.xlsx` 只是样例输入；`models_test/` 是模型压缩包，已排除；`ideas and structures/` 是设计笔记，不是运行代码。
