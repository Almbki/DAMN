# 前端接后端：这一层是怎么搭的

后端：`http://192.168.9.67:8000`（局域网另一台机器，FastAPI）。
接口文档：`docs/api.md`（**注意它和运行中的 schema 有几处对不上，以 `openapi.json` 为准**）。

## 分层（`damn-app/src/`）

```
api/          client.ts      fetch 封装 + ApiError + 错误翻译
              config.ts      base URL、前缀、超时
              endpoints.ts   每个端点一个函数（页面只调它）
              types.ts       后端 wire 类型（抄自 openapi.json）
              storage.ts     JWT / planId 的持久化（原生 SecureStore，Web localStorage）
              format.ts      日期与时长（后端给的是裸 wire 格式）
session/      session-provider.tsx   token 从哪来、何时作废
plan/         plan-provider.tsx      当前计划 + 生成 + 改任务 + 切版本
              selectors.ts           纯函数：今天有哪些、现在该做哪件、文案映射
components/   auth-screen.tsx        第一屏（未登录时由 _layout 直接渲染）
app/          5 个产品页 + account.tsx（退出登录 / 确认身份 / 看后端地址）
```

依赖方向：**页面 → plan/session → api**。页面里不允许出现 `fetch`。
`app/_layout.tsx` 是三层包裹：`ThemeModeProvider → SessionProvider → PlanProvider`，
未登录时**不渲染 `Slot`**，直接渲染登录界面（所以页面里一句「没登录怎么办」都不用写）。

## 配置

```bash
# damn-app/.env
EXPO_PUBLIC_API_BASE_URL=http://192.168.9.67:8000
```

- `EXPO_PUBLIC_*` 是**构建期内联**的：改完必须 `npx expo start --clear`。
- Android 模拟器里 `localhost` 是模拟器自己，要用 `http://10.0.2.2:8000`。
- Web 直连即可：后端 CORS 实测是 `access-control-allow-origin: *`。
- 真机连不上时先确认在同一网段（登录页页脚会显示实际请求的地址和 `/health` 探活结果）。

## 实测过的后端行为（不要凭文档猜）

用 `.shots/smoke-api.ps1` 和 `.shots/smoke-api-flows.ps1` 在真后端上验证过：

| 结论 | 影响 |
| --- | --- |
| `/health` 在**根路径**，不在 `/api/v1` 下 | `request(..., { root: true })` |
| `POST /plans/generate` **同步**返回（约 1.5 s），`status:"completed"` 且 `plan` 已内联 | MVP **不需要 SSE**；进度动画别伪造 |
| `GoalCreate.description` 的换行会成为 `TaskRead.standards` | 目标输入按行拆：首行当标题，其余当拆解线索 |
| 不传 description 也会有 multiple standards（单行目标实测 3 条） | 子步骤进度只在 `standards.length > 1` 时显示 |
| `PATCH {completed:true}` → `status` 变 `completed`，并写一条 `TaskExecution` | 勾选用它 |
| **`PATCH {completed:false}` 对 `completed` 的任务无效**（状态不变），对别的状态会打成 `pending` | 取消勾选必须显式发 `{status:'scheduled'}` |
| `PATCH {status:'in_progress'|'skipped'|'scheduled'}` 都生效 | 「开始」「今天先不做」用它 |
| 反馈 `completion_rate < 0.5` 会**自动新建一个计划版本**（`replan_plan_id`），老的标 `superseded` | 提交反馈后必须 `switchToPlan(replan_plan_id)`，否则界面还在展示旧版本 |
| 重排只保留**没做完**的任务 | 全做完时重排会得到一份 0 任务的计划 —— 空态必须处理 |
| 重排冷却**按用户**（默认 24h），命中时 409 `replan_not_eligible`，`detail` 里是完整的 `ReplanEligibilityRead` | 冷却提示要显示 `next_eligible_at`，别说"稍后再试" |
| 错误信封是 `{code,message,detail}`；但 Pydantic 422 是 FastAPI 默认结构 | `client.ts` 两种都解析 |
| 没有 refresh 接口，`expires_in` 7 天 | 401 直接清 token 回登录页 |
| `PlanRead.tasks` / `.goals` 在 schema 里是**可选**的 | `normalizePlan()` 统一补成数组 |
| 生成新计划会把**上一个 active 计划标成 `superseded`**（版本号继续递增：v4 → v5） | 不会覆盖，但"当前计划"只有一份；`listPlans` 里挑 `active` 的那份 |
| 后端在负载/争用时**单个请求能慢到 18 s**（实测 `/health` 18.3 s，同时未过鉴权的接口 0.36 s） | 普通请求超时定 30 s，别定 20 s（会误报超时） |

### ⚠️ 后端待修：`PlanRead.goals` 的映射是错的

实测（2026-09-19）：

| 计划 | 计划**真**的目标 | `GET /plans/{id}` 返回的 `goals` |
| --- | --- | --- |
| #5（1 个目标） | finish the half marathon plan | `[goal#1 'gaoshu limits review']` |
| #4（3 个目标） | thesis / defense / calculus | `[goal#1 'gaoshu limits review', goal#2 'single line goal', goal#3 'write chapter 3 of the thesis']` |
| #3（0 任务） | — | `[]` |

规律：**数量对得上**（等于该计划的任务所引用的 goal 数），但**标题取的是这个账号最早创建的 N 个目标**。
看起来是取 goals 时漏了按计划过滤 / 少了 join，只按 goal id 升序取了前 N 条。

影响：前端**目前没有任何页面渲染 `plan.goals`**，所以还没有把错的目标显示给用户。
但首页原设计那句「属于「目标」」要用它 —— **修好之前不要接**。
任务的 `goal_id` 仍然指向计划自己的目标（`task#6.goal_id=1`），所以"任务属于哪个目标"这条链是可用的，
不可用的是从计划反查目标。**

### 怎么复现这些结论

- 接口层：`.shots/smoke-api.ps1`、`.shots/smoke-api-flows.ps1`（ASCII-only；PS 5.1 会把无 BOM 的
  UTF-8 脚本按 ANSI 读，中文参数会变乱码）
- 界面层：`.shots/capture-all.ps1`（9 组视口/配色，带 token 注入）、
  `.shots/interact.ps1`（真点击 → 用**服务端状态**作为证据）、
  `.shots/interact-generate.ps1`（输入目标 → 生成 → 落到任务页）
- 这几个脚本都要 Edge headless，而 Chromium 的 IPC 在受限沙箱下会被拒
  （`FATAL:mojo platform_channel ... 0x5`）—— 整个脚本**一次性**放宽文件权限跑，别一个个提权。

## 时间字段的坑

- `"2026-09-19"`（`format: date`）用 `new Date()` 会按 **UTC 午夜**解析，东八区会退到前一天 →
  「今天是哪天」用 `toLocalDateString()` 本地拼，不要用 `toISOString().slice(0,10)`。
- `"08:00:00"`（`format: time`）**不是合法日期字符串** → `parseTimeToMinutes()` 自己拆。
- 只有带时区的完整 ISO（`created_at`）才可以直接 `new Date()`。

## 原生端必须重新构建

`expo-secure-store` 是**原生模块**（本次新增，`~57.0.4`）：

- Expo Go 自带，能直接用；
- 自己构建的 dev build / APK **必须重新构建**（`npx expo run:android` 或重新出包）。
  没重建时 `storage.ts` 会走兜底：令牌只存在内存里 + 打一条 `console.warn`，
  下次启动要重新登录 —— **不会崩**，但会让人以为"登录没保存"。

## 还没接的部分（明确列表）

- **`plan.goals` 一律没接**（后端映射有错，见上表下面的警告）。
- **SSE 六阶段进度**：`events_url` 没订阅。后端同步跑完才返回，做进度需要改成
  `react-native-sse` 或 fetch 流式解析（浏览器原生 `EventSource` **不能带 Authorization 头**）。
- **子步骤勾选**：`TaskUpdateRequest.standard_updates` 支持逐条勾 `standards`，UI 只显示进度。
- **任务级反馈**：`difficulty_feedback` / `stress_before|after` / `actual_duration` 字段后端都收，
  UI 只在勾选时发了 `completed`。
- **`users/me` 的资料**：`execution_weight` / `profile`（可用时间、作息）只读展示，没有编辑入口。
- **两周对比**：回顾页现在只统计**当前计划**（`insights` 是按 plan 的）。要做"这周比上周少几件"
  得再取上一份计划的 insights，并且注意后端每周会生成新计划版本。
- **`GET /plans` 的排序**：假设最新的在前（`listPlans` 取第一项 active）。多计划并存时值得再确认。
