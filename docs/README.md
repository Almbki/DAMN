# 文档索引（Docs Index）

> 先读这页，再按需跳转。⭐ = 权威/最新；⚠️ = 部分过时（内容仍可参考，但部分代码符号已变更）。

## 权威文档（本次校准，2026-10）

| 文档 | 内容 |
| --- | --- |
| ⭐ [`model-agent-integration-v1.md`](model-agent-integration-v1.md) | **本次三层模型 + Agent 重构交付**：真实 Level 1/2/3 运行时、Shadow Mode、PlannerRuntime/Workflow、迁移、验证、剩余风险 |
| ⭐ [`frontend-model-integration-v1.md`](frontend-model-integration-v1.md) | **前端 ↔ 三层模型对齐**：契约审计、Level 1 CAT 测评、Profile 两层、执行数据采集、Developer 页面、验证与风险 |
| ⭐ [`auth-demo-synthetic-v1.md`](auth-demo-synthetic-v1.md) | **V1.1 认证/引导/演示/合成数据**：Login/Register/Logout、Level 1 强制 Onboarding、重测冷却、IDOR、execution integrity、Synthetic Scenario Import/Reset |
| ⭐ [`streaming-and-callchains.md`](streaming-and-callchains.md) | **流式手册**：真流式架构与契约、Prompt 全清单（精确行号）、全功能调用链、画像摘出清单、LangGraph 注册点/边/工具 |
| ⭐ [`langgraph-state-machine.md`](langgraph-state-machine.md) | **LangGraph 权威文档**：两张图的节点/函数/文件行号、边与条件、Mermaid、状态键、工具、SSE 例外 |
| ⭐ [`project-structure-audit.md`](project-structure-audit.md) | **重构盘点**：项目树（排除 `models_test`）、分层、全部接口、模块清单、真实/假数据对照、ML 模块专项、已知风险 |
| ⭐ [`architecture-overview.md`](architecture-overview.md) | **架构总览**：分层、各层文件地图、数据模型、两条主链路、不变量、扩展接缝 |
| ⭐ [`development-handbook.md`](development-handbook.md) | **开发手册**：核心 vs 旁路、清理记录、已知缺陷、架构 checklist、调试清单 |
| ⭐ [`product-painpoints.md`](product-painpoints.md) | **痛点与需求建议**（信息不可信 / 拆解不可衡量 / backlog 等） |
| ⭐ [`replan-trigger-design.md`](replan-trigger-design.md) | **重排触发设计**：现状诊断、仲裁架构、新增任务、未完成 backlog |

## 主题文档

| 文档 | 状态 | 内容 |
| --- | --- | --- |
| [`modules.md`](modules.md) | ⚠️ 引用已删符号 | 逐模块详解 + 调用链 + 调试清单（正文仍很有用） |
| [`architecture.md`](architecture.md) | ⚠️ 过时 | 英文架构（仍提 `UserModelService` / 9 个 ORM / `app/ml/user_model.py`） |
| [`langgraph.md`](langgraph.md) | ⚠️ 自标 SUPERSEDED | 初版 6 节点原型；见 `agent/state-machine.md` |
| [`domain.md`](domain.md) | ⚠️ 含已删的 `UserModel` 章节 | 实体、枚举、7 条规则、排期、版本语义 |
| [`user-portrait.md`](user-portrait.md) | ⚠️ EWMA 已删除 | 旧画像说明；现以 `model-agent-integration-v1.md` 与 `app/user_models` 为准 |
| [`ml.md`](ml.md) | ⚠️ mock 已删除 | 旧预测器接口；生产已改为真实三层模型 + 确定性 estimate，Level 3 仅 shadow |
| [`agent/`](agent/README.md) | ✅ | Agent 层：state-machine / data-flow / prompts / tools / memory / testing |
| [`api.md`](api.md) · [`api-frontend-alignment.md`](api-frontend-alignment.md) | ✅ | 端点参考 + 前端契约对齐 |
| [`development.md`](development.md) | ✅ | 环境/命令（入门用；深度见 `development-handbook.md`） |
| [`research_direction.md`](research_direction.md) | ✅ | 论文检索方向（ML 变量 → Feature） |
| [`database/agent-migration.md`](database/agent-migration.md) | ✅ | Schema 迁移历史 |

## 快速定位

- **我是新接手的人** → `architecture-overview.md` → `development-handbook.md` §1（核心 vs 旁路）。
- **我要改代码** → `development-handbook.md` §5 checklist + §6「改哪里」。
- **我要做自适应/重排** → `replan-trigger-design.md`。
- **我要做需求规划** → `product-painpoints.md`。
- **我要调试** → `development-handbook.md` §7 + `modules.md` §10。
