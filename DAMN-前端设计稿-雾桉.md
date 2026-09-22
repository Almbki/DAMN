# DAMN 前端设计稿 v1 ·「雾桉」

> 状态：设计定稿，待落地。落地分支 `redesign/from-scratch`，目录 `frontend/`。
> 本稿批判性吸收《DAMN-双端统一UI设计方案.md》的技术实测结论，视觉定案全部重写。
> 配套调研：《DAMN-UI调研报告.md》《DAMN-双端前端架构调研.md》。

## 0. 对旧方案的批判性取舍

| 旧 v3 | 判定 | 理由 |
|---|---|---|
| 鲜艳琥珀 `#C67C10` + 薄荷绿 | ❌ 推翻 | 与"低饱和轻松感"直接冲突；高饱和暖色是催促感，不是"松一口气" |
| 两处毛玻璃 | ❌ 本期砍掉 | Android 接线复杂、深色要换"抬升白"、收益只是两处导航栏；页面未定稿前不为它付成本，留接口不留实现 |
| 凹/平/凸/浮四档高度语义 | ✅ 保留（放宽） | 凸=与页面有高度差（可点、卡片、浮层），凹=已发生；列表行/区块/图表保持扁平 |
| 静态内容用发丝线分区 | ✅ 保留 | 列表行/区块/图表保持扁平；阴影只表达"浮起来"这一件事 |
| 焦点环 = 输入模态追踪 + 1.5px 描边 | ✅ 保留（细化） | 三端行为一致，不依赖 CSS 伪类；鼠标点击不出环，只在键盘导航时出环 |
| mono 大数字时长为页面主角 | ✅ 保留 | 用户卡住的是"要花多久"，不是"做什么" |
| 60px 竖栏 / 4 档断点 | ⏸ 推迟 | 页面结构未定，壳维持现状两档（768），页面定稿后再分档 |
| 5 页结构（index/tasks/goals/assessment/review） | ❌ 推翻 | 按新页面集：TODO / 画像 / GOAL / 设置（见第 7 节） |

## 1. 色彩 · 雾桉（低饱和冷灰绿）

| token | light | dark | 用途 |
|---|---|---|---|
| paper | `#F5F6F3` | `#151816` | 页面底 |
| panel | `#EDEFEA` | `#1C201D` | 导航/面板底 |
| raised | `#FFFFFF` | `#1C201D` | 抬起面（深色靠叠白 0.07，非阴影） |
| line | `#E2E5E0` | `#2A2F2B` | 发丝线 |
| ink | `#252924` | `#E6E9E4` | 正文（非纯黑/纯白） |
| inkMuted | `#5F665F` | `#9BA39B` | 次要文字 |
| inkFaint | `#9AA098` | `#6A7269` | ⚠️ 仅非文字用途（刻度/分隔/图标），对比度不够 AA |
| accent | `#4F7A66` | `#96BFA9` | **只给"现在"**：当前项、主按钮、进度 |
| accentSoft | `#E0EAE4` | `#223129` | 当前项底色 |
| onAccent | `#FFFFFF` | `#101512` | accent 上的文字 |
| hover | `rgba(37,41,36,0.05)` | `rgba(230,233,228,0.06)` | 悬停叠层（不换填充色） |
| pressed | `rgba(37,41,36,0.09)` | `rgba(230,233,228,0.10)` | 按压叠层 |
| ripple | `#252924` | `#E6E9E4` | 按压光晕底色（动画 opacity 到 0.18 再淡出） |
| rippleOnAccent | `#FFFFFF` | `#101512` | accent 面上的光晕底色 |
| navPill | `#FFFFFF` | `#333833` | 底栏激活滑块（浅色胶囊） |

纪律：
1. accent 只标记"现在这一件"；完成态不引入第二个彩色（ink 60% + 删除线）。
2. 不用 tonal 彩色填充块、不用渐变。
3. 组件只引用角色 token，一个颜色字面量都不许出现。

## 2. 高度四档（唯一阴影入口 = `Surface` 组件）

**微拟物 / MD 分工的裁定**：与页面底有高度差的组件走微拟物凸起，扁平内容与动效走 MD。落地口径：

- **走凸起**（`raised` / `inset`）：卡片类容器（画像状态格与周趋势卡、GOAL 目标卡与拆解/对话卡、TODO 反馈区、设置卡）、按钮、浮层。即把旧的"凸=可点"放宽为"凸=与页面有高度差"。
- **保持扁平**（`flat` + 发丝线）：任务列表行、区块标题、图表（条形/进度）、行内分区。**列表行永远不挂阴影。**
- 凸起面靠阴影/叠白表达"浮起来"；卡片不再叠发丝线边框（按钮的 1px 描边保留，作边缘定义）。

| 档 | 语义 | light | dark |
|---|---|---|---|
| flat | 可读不可点（列表行/区块/图表） | 无阴影，发丝线分区 | 同左 |
| raised | **与页面有高度差**（卡片/按钮） | `0 1px 2px rgba(30,34,31,.09), 0 6px 18px rgba(30,34,31,.13)` | 叠白 `rgba(230,233,228,0.07)` + 顶部发丝线高光 `rgba(230,233,228,0.14)` |
| overlay | 浮层（弹层/抽屉/计时浮条） | `0 12px 36px rgba(30,34,31,.22), 0 2px 8px rgba(30,34,31,.10)` | 叠白 0.11 |
| inset | **已发生**（按下/选中/已勾选） | `inset 0 2px 4px rgba(30,34,31,.18), inset 0 -1px 0 rgba(255,255,255,.70)` | `inset 0 2px 5px rgba(0,0,0,.62), inset 0 1px 0 rgba(255,255,255,.05)` |

- 跨端统一 `boxShadow`（RN 0.86 对 iOS/Android/Web 全支持含 `inset`）；**禁用** `shadowOffset/shadowOpacity/shadowRadius`（仅 iOS）。
- 阴影色由冷灰绿背景派生，不用纯黑、不用暖棕。暗色不投外阴影。
- 同一元素不许同时挂阴影和（将来的）毛玻璃；焦点环永远盖过阴影。
- 长列表逐行不加阴影（低端 Android 合成开销）。

## 3. 圆角（跟层级走，越大越浮）

`4` 行内标记 · `8` 控件与凹面 · `12` 列表容器 · `16` 卡片/辅栏 · `20` 弹层 · `full` 圆形完成键。
凹面圆角比所在容器小一档。

## 4. 字体与排版

- 中文系统栈；拉丁与数字 IBM Plex Mono（已加载）。
- **时长数字 = 全页最大元素**（mono 大字），这是唯一保留的"主角"。
- 字阶一套到底，双端只分密度不分字号；行宽 ≤80 字符；中文行高 ≥1.5；字重只用 400/700。
- 不做：all-caps eyebrow、单词变色强调、中点连接的 meta 串。

## 5. 动效（MD3 token，只回应操作）

- duration：`short: 150/200` · `medium: 300` · `long: 500`
- easing：standard `cubic-bezier(0.2,0,0,1)` · decelerate `cubic-bezier(0.05,0.7,0.1,1)`（入场）· accelerate `cubic-bezier(0.3,0,0.8,0.15)`（离场）
- 按压：scale 0.98 @150ms。Web 用 CSS transition（只动 transform/opacity）；原生本期直接切换，reanimated 后置。
- 点击光晕（MD ripple）：按下点生成圆，`scale 0 → 2.2` + `opacity 0.18 → 0`，350ms，decelerate 曲线，播完即移除。挂到主/次按钮、Segmented、任务行、导航项。用 RN `Animated`（只动 transform/opacity），跨端同一份代码；尊重 `useReducedMotion`。
- 完成态过渡：勾选未完成任务时，该行 300ms 内 `opacity 1 → 0`、`translateY 0 → -8px`，动画结束后才从列表移除（reduced motion 下直接移除）。
- 底栏高亮滑块：单一 `Animated` 节点的 `translateX`，位置 = 激活序号 × 单项宽度（宽度 `onLayout` 量容器后计算，不用 `flexWrap`）；切换 300ms `Duration.medium` + `Easing.decelerate`，只动 transform，`Motion.nativeDriver`；关闭动效时直接跳位。
- 焦点环只回应键盘：`pointerdown` 进鼠标模态、`Tab`/方向键进键盘模态，只有键盘模态渲染 1.5px accent 描边；浏览器默认 outline 由 `global.css` 抑制。实现见 `hooks/use-input-modality.ts`。
- 无入场表演、无滚动触发动画；尊重 `prefers-reduced-motion`（已有 `hooks/use-reduced-motion.ts`）。

## 6. 编码红线（落地时必须遵守）

1. 页面里不出现 DOM：不 import react-native-web 专属 API、不碰 `document`/`window`；`Platform.OS` 只允许在 `components/shell*` 与 `constants/`。
2. 所有阴影/叠白/圆角档只在 `Surface` 里实现，组件不自写阴影。
3. 不用 `flexWrap` 做布局（RNW 会吃掉它）——换行按列数显式分行。
4. 中文换行由 `src/global.css` 的 `white-space: normal !important` 兜底，组件不改 `white-space`。
5. 任何可点元素命中区 ≥44pt（触屏）；焦点环只有键盘模态（`pointerdown` → 鼠标、`Tab`/方向键 → 键盘）才渲染，1.5px accent 描边，鼠标点击不出环；浏览器默认 outline 在 `global.css` 里抑制。
6. 不用 `@expo/ui`、`expo-glass-effect`（无 Web 实现）。
7. 原生边界不写 `as any`/`@ts-ignore` 强转。
8. 导航图标只用手写线性 SVG（`components/icons.tsx`，stroke 1.75、无填充、圆头），不引入图标字体或第三方图标库。
9. 高度语义按第 2 节分工：与页面有高度差的组件（卡片类容器、按钮、浮层）走 `raised`/`inset`；任务列表行、区块、图表、发丝线分区保持 `flat`——不要把静态行也做成卡片。
10. 顶栏不再放页面标题与主题切换；它只承载当前页面注入的控件（`components/shell/header-controls.tsx` 的槽）。

## 7. 页面规格（一级页，无二级页；拿不准的跳过；本期全部 mock 数据）

路由：`/` TODO · `/profile` 画像 · `/goals` GOAL · `/settings` 设置。

导航（宽档竖栏与窄档底栏）每项 = 手写线性图标 + 文字；宽档图标在文字左侧，窄档图标在上、文字在下；当前项图标用 accent、其余用 inkMuted，命中区 ≥44pt。窄档底栏的激活项另有浅色胶囊滑块（见第 5 节），激活项图标与文字上浮、文字加粗。

顶栏（`AppShell`）不放标题、不放主题切换，只承载页面注入的控件：TODO 页把左上视图/分组切换与右上计划变更提示注入窄/宽一致的顶栏；其余页面顶栏为空。主题切换移入设置页。

旧 `feedback.tsx` 删除（每日反馈并入 TODO 页底部）。旧页面组件（now-card/ruler/timeline/task-row/task-editor/task-meta/batch-bar/smart-list-tabs/why-note）全部删除重写。
保留接线层：`src/api`、`src/domain`、`src/state`、`src/hooks`、`src/data/mock.ts`（按需扩）、`src/global.css`。

### 7.1 TODO（`/` 主页）

- 三个视图切换：今日 / 本周 / 每月（Segmented，选中即 inset 凹面）——留在页面内容区。
- 顶栏左：按钮切换「只看未完成 ⇄ 按分组」。
- 任务列表：圆形完成键 + 标题 + mono 时长，勾选即完成（行内 inset 微反馈，0.3s 内淡出上移）；列表行保持扁平 + 发丝线。
- 顶栏右：计划变更提示——系统改了未来哪几天，一眼看见（一个小标记 + 点开浮层列出变更；浮层用 overlay 档，层级盖过内容）。
- 每个任务可开始专注：行内展开计时器——正计时，或可配置倒计时（工作多久 / 休息多久 / 几轮，三个数字输入）。计时用简单 setInterval 即可，不做后台持久。
- 页面滚动到底部：每日反馈区（精力/压力/心情各一档选择 + 提交按钮，提交后显示"已记录"态），容器走 `raised`。

### 7.2 画像（`/profile`）

- 当前状态三格：精力 / 压力 / 效能（大数字 + 档位词），格容器走 `raised`。
- 趋势曲线：无 svg 依赖，用 View 条形图近似（7 天），容器走 `raised`。
- 数据够不够：一行说明（"已有 12 天数据，趋势可信"这类）。
- 「系统为什么这么判断」：一段归因文字 + 左侧 accent 竖线（why-note 样式），扁平。

### 7.3 GOAL（`/goals`）

- 目标列表 + 进度条（按时间加权的 mock 值，配百分比 mono 数字），目标卡走 `raised`。
- 「添加目标」按钮 → 页内进入拆解流程（不是二级页）：草案预览（任务列表）→ 边编辑边和 AI 对话澄清（mock 对话区，预置几轮假对话）→ 确认。拆解/对话卡走 `raised`，对话气泡走 `inset`。
- 中途取消：目标存为草稿（列表里显示"草稿"态），不用重填。

### 7.4 设置（`/settings`）

- 外观：深浅色三态（浅色 / 深色 / 跟系统）用 Segmented，一个设置项。
- 账号信息块（mock 用户）。
- 排程偏好表单：每日可投入时间、单日上限、缓冲时间、高认知任务上限——设一次就一直生效（存入 state/持久化 mock，不再每次重填）。

## 8. 落地顺序

1. `constants/tokens.ts` 按第 1–5 节重写（Palette 键名改为本稿语义，全部引用点一并迁移，typecheck 兜底）。
2. 新增 `components/surface.tsx`（四档高度 × 圆角，唯一阴影实现处）。
3. `constants/nav.ts` 改四项：TODO/画像/GOAL/设置。
4. 四个页面按第 7 节重写；旧组件删除。
5. `npm run typecheck` + `npm run lint` 必须通过。
6. 验收：Edge 无头截图 390/768/1440 × 明/暗。
