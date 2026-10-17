# 开发手册（Development Handbook）

> 面向未来开发：**什么是核心框架**、**本次删了什么/为什么保留什么**、**加代码时必须遵守什么**、**已知缺陷**。
> 配套：`docs/architecture-overview.md`（架构）、`AGENTS.md`（命令与硬规则）。

---

## 1. 核心框架 vs 可选旁路（最需要先建立的认知）

产品闭环是：**生成 → 落库 → 执行 → 反馈 → 画像 EWMA →（路由）→ 重排**。凡是**不在**这条闭环上的能力，都是可选旁路。

### 1.1 不可移除的核心（CORE）

| 类别 | 模块 |
| --- | --- |
| 入口/契约 | `app/main.py`、`app/api/**`、`app/schemas/**`、`app/core/**`（配置、安全、鉴权） |
| 编排 | `app/application/services/`：`plan_service`、`feedback_service`、`goal_service`、`replan_service`、`profile_service`、`auth_service` |
| 领域 | `app/domain/models/**`、`app/domain/rules/**`、`app/domain/scheduling/**`、`app/domain/profile/engine.py` |
| 基础设施 | `app/infrastructure/database/**`、`app/infrastructure/llm/client.py` |
| 智能流程 | `app/agent/**`（两个图 + 节点 + 工具 + state + checkpointer + prompts）——**这就是产品的计划生成管线** |
| 预测接口 | `app/ml/base.py` + `predictors.py` + 已接入的实现（即便当前是统计 mock） |

**判据**：拿掉它，闭环就断。`profile_service` 在生成热路径上（EWMA 状态 → `UserFeatureSet` → 预测器 → 草稿），必须归为核心。

### 1.2 可选/实验旁路（可关、可换、可删）

| 旁路 | 现状 | 建议 |
| --- | --- | --- |
| Agent 记忆子系统（`memory_service` + `agent_memories` + `memory/*`） | best-effort，反馈里可失败 | 不影响生成；可先隔离到开关后 |
| `insight_service` / `situation_service`（趋势、洞察） | 只读分析，不在闭环 | 保留，非关键路径 |
| 生成 SSE 回放（`generation_service`） | 同步跑完后回放事件 | 见 §4 缺陷 #5（“剧场”）；可换成轮询 |
| `prediction_logs` 评分脚本 | 无训练模型时是噪声 | 保留表+写入（数据资产），脚本移出关键路径 |
| `app/ml` 统计 mock | 可替换 | 保留接口 + 1 个实现 |

---

## 2. 环境与命令

```bash
uv sync --extra dev                 # 安装（需 Python 3.12）
uv run pytest                       # 全部测试（当前 170）
uv run pytest -k scheduler -v       # 排期相关
uv run pytest tests/integration/test_plan_flow.py -v   # 端到端闭环
uv run ruff check .                 # 静态检查（line length 100, py312）
uv run uvicorn app.main:app --reload # 起服务 → http://localhost:8000/docs
uv run alembic upgrade head         # Postgres 建表/迁移
```

- `README.md` 必须存在（`pyproject.toml` 声明 `readme`，删掉会导致 `uv sync` 失败）。
- `tests/conftest.py` 在 `import app` **之前**设置 `DATABASE_URL` / `JWT_SECRET_KEY`，然后清 settings 缓存——新测试保持该顺序。
- Windows 某些端口被系统占用会导致 `WinError 10013`，用 8000。

---

## 3. 本次清理记录（已删除的死代码）

> 清理原则：**只删“无任何调用者、且不是刻意保留的接缝”的代码**。改动满足 `ruff` 通过 + 170 测试全绿（净 −502 行 / +19 行，29 个文件）。git 历史可恢复。

### 3.1 已删除

| 位置 | 删除内容 |
| --- | --- |
| `schemas/plan.py` | `ConfirmRequest`；`ReplanRequest.from_date`（从未被消费） |
| `schemas/profile.py` | `ProfileUpdate`（含 `__init__` 导出） |
| `application/dto/plan.py` | `PlanDetail.plain_tasks` 属性 |
| `services/plan_service.py` | `PlanService.generate_plan`（仅 `generate_plan_with_events` 在用）；被忽略的 `user_features` 形参 |
| `services/generation_service.py` | `_default_service_factory`（与 `deps.py` 重复的组合根） |
| `services/profile_service.py` | `prompt_block`、`resolved_mbti`（+ 未用的 `resolve_mbti_type` import） |
| `services/memory_service.py` | `get_memories`、`forget` |
| `services/feedback_service.py` | 未被注入的 `memory_service`/`profile_service` 构造参数 |
| `core/logging.py` | `get_logger` |
| `core/config.py` | `Settings.is_development` |
| `dto/generation.py` | `AgentEvent.progress`（`from_dict` 从不赋值） |
| `domain/scheduling/scheduler.py` | 模块级 `schedule_tasks()` |
| `domain/scheduling/schedule_result.py` | `ScheduleResult`、`ScheduledTask.deadline_risk` |
| `agent/graph.py` | `PlannerGraph.extract_final_plan` / `invoke` / `run_with_events`、`create_planner_graph`、`RunMetadata` 注入 |
| `agent/nodes/_shared.py` | `preferences_block`、未用的 `DEFAULT_DAY_START/END` |
| `agent/tools/base.py` | `describe_schema`、`ToolRegistry.all`/`llm_tools`（仅测试用） |
| `agent/tools/user_statistics.py` | **整个文件** + 注册项（已注册但从不调用） |
| `agent/state.py` | `PreviewActionRequest`/`FeedbackCycleRequest`/`ReplanTriggerRequest`/`RunMetadata`；只写不读的扁平键 `predicted_duration`/`predicted_completion_probability`/`stress_estimation` |
| `agent/schemas.py` | `PreviewAdjustmentRejected` |
| `agent/checkpointer.py` | `reset_checkpointer` |
| `agent/prompts/__init__.py` | `list_prompts`、`clear_prompt_cache` |
| `agent/router.py` | `route_after_classify`、`IntentRoute`（图 A 实际是 `classify_request → goal_analysis` 无条件边） |
| `agent/prompts/repair.md` | 从未被加载（`plan_repair` 刻意无 LLM） |
| `tests/` | 两个引用已删符号的测试（`test_hardening_guards` 的 run_with_events 用例、`test_tools` 的对应用例） |

### 3.2 **刻意保留**的“看似无用”代码（不要当死代码删）

| 保留项 | 为什么保留 |
| --- | --- |
| `app/infrastructure/ml/model_store.py` | 明确的**roadmap 接缝**（将来加载训练模型），隔离且零成本 |
| 仓储里暂未调用的 CRUD（`list_by_plan_and_date`、`delete_by_plan`、`get_by_plan_and_date`、`get_by_run_id`、`get_latest_for_plan`、`list_by_task` 等） | 常规仓储面；未来洞察/趋势/清理任务会用到，删了只会再写回来 |
| `domain/profile/engine.py` 的 `predict_duration`/`predict_completion`/`should_prompt` | 画像规范里的**领域策略**（纯函数、有测试、被文档引用），是 ML 接缝 |
| `ReplanRequest.from_date` 之外的重排字段 | 属于对外契约 |

> 若后续采用“方法必须有调用者”的严格策略，可再删 3.2 的仓储方法；但那属于策略选择，不是死代码。

---

## 4. 已知缺陷与风险（按优先级）

> 本次**未改**这些（超出“清理 + 文档”范围）；建议按序修复。

| # | 问题 | 位置 | 影响 | 优先级 |
| --- | --- | --- | --- | --- |
| 1 | `confirm_plan` 的 pending 分支调用 `self.get_plan(user_id, 0)` → 必抛 `NotFoundError` | `services/plan_service.py`（`# pragma: no cover` 分支） | 潜在真 bug，一旦命中即 500/404 | P0 |
| 2 | `DEFAULT_HORIZON_DAYS` 三处不一致：`api/v1/plans.py`=13、`plan_service.py`=13、`scheduler.py`=14；`plans.py` 还有裸 `timedelta(days=13)` | 多处 | 静默 off-by-one，horizon 漂移 | P1 |
| 3 | 反馈路径**无冷却/预算**：自由文本必触发全量重排；2 天低完成即可重排 | `agent/router.py`、`feedback_service.py` | 计划版本抖动、用户信任受损 | P1 |
| 4 | 反馈驱动的**全量重排被记为 `MANUAL`**（trigger_type 误标）；`changed_task_ids` 返回新版本**全部**任务 | `plan_service.py` | 破坏用于校准的 `replan_events` 数据 | P1 |
| 5 | ~~`POST /plans/generate` 返回 **202** 但同步执行完整流水线~~ **已修复**：generate/replan/decompose 现在都是真异步 job + 实时 SSE | `api/v1/plans.py`、`generation_service.py` | 见 `docs/streaming-and-callchains.md` | ✅ |
| 6 | `PATCH` task 传入 `actual_duration`/`failure_reason` 等：`TaskORM` 无这些列，**静默丢弃**（除非 `completed=true`） | `api/v1/tasks.py`、`plan_service.update_task` | 静默数据丢失，比 422 更糟 | P2 |
| 7 | 应用层反向依赖 API schema（`goal_service` 用 `GoalCreate/Update`；`situation_service` 直接返回 `SituationTrendRead`） | `services/goal_service.py`、`situation_service.py` | 层反转，会自我复制扩散 | P2 |
| 8 | API 层构造 ORM 实体（`feedback.py` 里 `Feedback(...)`） | `api/v1/feedback.py` | 同上层反转 | P2 |
| 9 | Scheduler 预检与 RuleEngine 策略重复（每日上限/缓冲/学科冲突；`HIGH_GAP_MINUTES` 两处复制） | `scheduler.py` vs `rules/*` | 策略漂移：改一处忘另一处 | P2 |
| 10 | `confirm_preview` 201 vs `confirm_draft` 200 | `api/v1/plans.py` | 契约不一致 | P3 |
| 11 | `dto/plan.py` 内嵌 ORM 实体（`TaskWithStandards`/`PlanDetail`） | `application/dto/plan.py` | 承载式技术债，暂不动 | P3 |

---

## 5. 加代码时的架构 checklist

1. 先问：这是**核心闭环**还是**可选旁路**？不要在核心路径里塞实验代码。
2. 依赖只能向内：`api → application → domain`；`infrastructure` 依赖 `domain`；**domain/core 绝不 import FastAPI/SQLAlchemy**。
3. Agent 不碰 DB：新数据走 `RepoContextBuilder` / `PlanService` 注入。
4. 硬约束只加到 `domain/rules/` 并在 `default_rules()` 注册，`name`/`code` 唯一。
5. Service 拥有事务；repo **只 flush**。
6. 新 API 不返回 ORM/领域对象，一律经 `mappers.py`。
7. 新字段要**同时**改 4 处：domain model、ORM model、schema、（迁移）。
8. mock/占位必须在 docstring 明确标注，别谎称有训练模型。
9. 改图/节点：SSE stage 名必须等于节点名；节点输出必须是 `agent/schemas.py` 的结构化对象。
10. 改 plan/feedback/replan 流程：同步更新 `tests/integration/test_plan_flow.py`。

---

## 6. 常见需求改哪里

| 需求 | 改这些文件 |
| --- | --- |
| 新增硬约束 | `domain/rules/<new>.py` + `default_rules()` |
| 换真实 LLM | `infrastructure/llm/client.py` 实现 `LLMClient`；`LLM_PROVIDER` |
| 换某个 Agent | 对应 `agent/nodes/<node>.py` |
| 接入真实 ML | `app/ml/` 实现 4 个 Protocol；`PlanService(predictors=…)` |
| 换排期算法 | `domain/scheduling/scheduler.py::Scheduler.schedule` |
| 换数据库 | `infrastructure/database/repositories/*` |
| 新增 API | `api/v1/<res>.py` + `router.py` + `schemas/<res>.py` + `mappers.py` |
| 调画像公式 | `domain/profile/engine.py` + `tests/unit/test_profile.py` |
| 调重排策略 | 见 `docs/replan-trigger-design.md` |

---

## 7. 调试清单（按症状）

| 症状 | 先看 |
| --- | --- |
| 计划无任务 | `agent/nodes/plan_generation.py` → `graph._finalize` → `PlanService._persist_plan` |
| 有任务但排不上期 | `domain/scheduling/scheduler.py`；`CandidateSchedule.unscheduled_task_ids` |
| 超每日上限 / 学科冲突 | `domain/rules/*` + `agent/nodes/validation.py::build_rule_context`（检查 `task_subjects` 临时 id 映射） |
| 修复循环不收敛 | `graph._should_repair`、`repair_attempts`/`max_repair_attempts`、`nodes/repair.py` |
| SSE 只有 `completed` | `GenerationEvent.stage` 是否=节点名；`generation_service.stream_sse` |
| 重排 409 | `ReplanService.check_eligibility`（用户级冷却）→ `replan_events` 最新记录 |
| 完成率低却不重排 | `agent/router.py` 的覆盖条件、`profile_service.replan_decision_for` |
| 401/token | `core/security.py`、`api/deps.py::get_current_user`、`JWT_SECRET_KEY` 长度 |
| Postgres 表不存在 | 只跑了 `init_db()`（仅 SQLite）；执行 `alembic upgrade head` |
