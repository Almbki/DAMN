# DAMN 双端前端架构调研（Expo SDK 57 / RN 0.86.3 / expo-router）

调研对象：`damn-app`（本地实测：expo ~57.0.24、expo-router ~57.0.22、react-native 0.86.3、
react-native-web ~0.21.0、`app.json` 已设 `web.output = "static"`）。
「文档明确写的」与「社区经验/推断」在下文分别标注，查不到的写「未能核实」。

---

## 0. 一句话结论

**推荐「一套响应式代码 + 平台后缀的导航壳」**，并且**不要新建独立 Web 控制台**。
理由：DAMN 现有结构（`src/components/app-tabs.tsx` + `app-tabs.web.tsx`）**就是 Expo 官方文档里点名的推荐写法**，
成本已经付过了；再拆两套布局等于在 3 天 / 0 React 基础的约束下把工作量翻倍。

---

## 1. expo-router 的多端布局策略

### 1.1 官方给了三条路（都是文档明写的）

来源：[Platform-specific extensions and module](https://docs.expo.dev/router/advanced/platform-specific-modules/)

| 方式 | 写法 | 适用 | 官方态度 |
|---|---|---|---|
| 平台后缀文件 | `_layout.web.tsx`、`app-tabs.native.tsx` | 整个布局/组件换掉 | 明确支持；**`src/app/` 内使用后缀时必须同时存在非平台版本**，以保证深链路由一致 |
| `Platform.OS` 分支 | `if (Platform.OS === 'web') return <Slot/>` | 单文件内小分叉 | 文档给了完整示例（Web 用 `<Slot/>` + 自定义 header，原生用 `<Tabs>`） |
| 共享组件 + 平台扩展 | `_layout.tsx` 引 `AppTabs`，`app-tabs.tsx` / `app-tabs.web.tsx` | 布局骨架共用、导航壳分叉 | 文档给了两个完整示例，其中第二个（`app-tabs.tsx` + `app-tabs.web.tsx`）**与 DAMN 现状逐字一致** |

**没查到**官方文档说「哪种最好」的排序，也没查到针对「同一 App 手机+浏览器」的响应式导航官方示例页。

### 1.2 group / 布局组织（文档明写）

| 组件 | 作用 | 何时用 |
|---|---|---|
| `(tabs)` 目录 + `Tabs` | React Navigation bottom tabs；`href: null` 可隐藏某项 | 底部标签栏 |
| `NativeTabs`（SDK 55–57 走 `expo-router/unstable-native-tabs`） | 系统原生标签栏，必须在 layout 里显式写 `NativeTabs.Trigger` | 要原生手感 |
| `(drawer)` + `Drawer` | 侧滑抽屉，可与 tabs 嵌套 | 全局工具入口 |
| `Stack` | 压栈 + 原生 header | 二级页 |
| `Slot` | **不引入导航器**，只包一层 header/footer | Web 侧边栏壳、控制台式布局 |

嵌套：官方 `nesting-navigators` 文档说明「同一目录不需要额外 `_layout`，只有真正需要新导航器时才嵌套」；
Expo 官方博客 [Nesting tabs and drawers](https://expo.dev/blog/nesting-tabs-and-drawers-with-expo) 给了
`(drawer)/_layout.tsx → (tabs)/_layout.tsx` 的完整可抄结构，并明确建议：
**3–5 个平级页面就用纯底部标签，硬塞抽屉只会增加认知负担**（DAMN 是 5 个页面，正好落在这条建议的"不要加抽屉"区间）。

### 1.3 `unstable-native-tabs` 成熟度与限制

文档：[Native tabs](https://docs.expo.dev/router/advanced/native-tabs/)、
API [Router Native tabs](https://docs.expo.dev/versions/latest/sdk/router/native-tabs/)（v57.0.0）

- **能自定义，但只能改"原生允许你改的"**：`backgroundColor`、`indicatorColor`（Android/Web）、
  `iconColor`、`tintColor`、`labelStyle`、`badgeBackgroundColor`、`rippleColor`（Android）等。
  `Icon` 支持 `sf`（iOS）、`md`（Android Material Symbols）、`src`（图片）、`xcasset`。
- **SDK 57 仍是 `unstable_` 前缀**（SDK 58 起搬到 `expo-router/native-tabs`），
  `unstable_nativeProps` 文档自述「may change or be removed in minor versions」。
- 文档明列的**已知限制**：

| 限制 | 影响 |
|---|---|
| Android 最多 5 个 tab（Material 组件限制） | 5 个页面是上限，无余量 |
| 不能嵌套原生 tabs | 只能嵌 JS `Tabs` |
| 无法测量 tab 栏高度（文档原话：正在做） | `BottomTabInset` 只能硬编码（DAMN 就是 `ios:50/android:80`） |
| 不支持运行时增删 tab（会 remount、丢状态） | tab 必须静态定义 |
| FlatList 支持有限（scroll-to-top / 收起） | 长列表要 `disableTransparentOnScrollEdge` |
| iOS 18 及以下滚动到底会变透明；iOS 26 背景属性失效 | 主题适配的坑 |
| 所有 tab 屏幕 eager 渲染，不可改 | 首屏成本 |

- **Web 端**：API 页写 `NativeTabs` 支持 Web，但指南明说「Web 上没有系统 tab 栏，
  native tabs 会**降级为一个基础实现**（大致照 iPad 设计）」。→ **不要把 Web 端观感押在 NativeTabs 上**，DAMN 现在 Web 走 `expo-router/ui` 是对的。
- **Android 社区已知问题**（GitHub issue，非文档）：
  [expo/expo#41031](https://github.com/expo/expo/issues/41031)（用 `src` 图片图标在 Android
  production/preview 包里不显示，标签为 upstream react-native-screens，**2026-01-13 已 closed/completed**）；
  [expo/expo#41781](https://github.com/expo/expo/issues/41781)（`NativeTabs.Trigger.hidden` 在 Android 无效，
  **2026-05-24 被 stale 机器人自动关闭，不代表已修复 —— 未能核实是否真正修好**）。
  → 结论：**Android 上别依赖 `hidden` 隐藏 tab，改用不渲染 Trigger**。
- 另有一条值得知道的风险：SDK 57 上**经典 `Tabs`**（非 native tabs）在 iOS release 构建有
  "卡在启动图 / Fabric 首帧不挂载" 的 issue（[expo/expo#47687](https://github.com/expo/expo/issues/47687)），
  描述指向「每个 tab 内再嵌 Stack」的写法。DAMN 用的是 NativeTabs，且只有 2 层，风险较低，但**上真机 preview 构建后必须实测一次**。

### 1.4 有没有官方"窄屏=底栏 / 宽屏=侧栏"模式？

**有，但在 React Navigation 侧，不在 Expo Router 侧。** 官方文档
[Bottom Tabs Navigator](https://reactnavigation.org/docs/bottom-tab-navigator/) 的 `tabBarPosition` 一节，
给出了用 `useWindowDimensions()` + `dimensions.width >= 768 ? 'left' : 'bottom'` 切换成侧栏的**官方示例代码**，
并说明 `tabBarPosition: 'left'|'right'` 时「styled as a sidebar」，配合 `tabBarVariant: 'material'` 可做紧凑侧栏。
Expo 的 [JavaScript tabs](https://docs.expo.dev/router/advanced/tabs/) 页把 `tabBarPosition` / `tabBarVariant`
列为 `Tabs` 支持的选项 —— **但该表把平台标为 "Android, iOS"，我没有查到任何官方说明它在 Web 端的表现，标记为未能核实**。
它**不适用于 NativeTabs**（NativeTabs 的 API 里没有 `tabBarPosition`，只有 iOS 18+ 的 `sidebarAdaptable`，
且文档说该属性在 iPhone 上无效）。

---

## 2. Expo SDK 57 Web 端的真实成熟度

### 2.1 定位与导出模式

SDK 57 = RN 0.86，发布于 2026-06-30，官方定性为"小而聚焦、无破坏性改动"的一版
（[SDK 57 changelog](https://expo.dev/changelog/sdk-57)）。注意 `expo@57.0.17`（RN 0.86.3）才修掉
Hermes 相关内存/启动回归 —— DAMN 用的 57.0.24 已包含。

`react-native-web`（本项目 ~0.21.0）在 Expo 里的定位：[Develop websites](https://docs.expo.dev/workflow/web/)
明确写 RNW 是 `<View>/<Text>` 到 `div/p/img` 的包装层，「**是可选但推荐的**，跨端时能最大化代码复用」，
并说 X（Twitter）整站就是 RNW 驱动。SDK 里所有库「都为浏览器和服务端渲染环境构建」。

`web.output` 三选一（[Publish websites](https://docs.expo.dev/guides/publishing-websites/)）：

| 模式 | 产物 | 动态路由 | 需要服务器 | DAMN |
|---|---|---|---|---|
| `single`（默认） | 单个 index.html（SPA） | 客户端路由 | 否 | — |
| `static` | 每个路由一个 HTML | 需 `generateStaticParams` | 否 | **当前使用** |
| `server` | client/ + server/，请求时渲染 | 自动 | **是**（SDK 55–57 还需 `unstable_useServerRendering` 开关） | — |

对 DAMN 的意义：[Static rendering](https://docs.expo.dev/router/web/static-rendering/) 文档明确
**`static` 模式下不支持请求时渲染**，且「不是 SPA，没有自定义 server API」；`+html.tsx` 里**不能 import 全局 CSS**
（要用 root layout）；字体要静态优化必须同步 `useFonts`。→ 演示/静态展示完全够用，**不要**因为想要"控制台"而去碰 `server`。

### 2.2 各模块在 Web 上到底行不行（文档平台字段核实）

| 模块 | Android | iOS | Web | 备注 |
|---|---|---|---|---|
| `expo-symbols` | ✓ | ✓ | **✓** | iOS=SF Symbols，**Android/Web=Material Symbols**。文档明确：**只传字符串只会在 iOS 渲染**，Web/Android 什么都不显示，必须传 `{ios, android, web}` 对象或给 `fallback` |
| `expo-image` | ✓ | ✓ | ✓ | Web 上额外有 `loading`、`responsivePolicy`（`static` 默认可配静态渲染）与 `webMaxViewportWidth`（文档已标 deprecated） |
| `react-native-reanimated` 4.5 | ✓ | ✓ | ✓ | 官方 [Web Support](https://docs.swmansion.com/react-native-reanimated/docs/guides/web-support/) 明说：Web 上「全部功能都是纯 JS 实现，**效率可能更低**」 |
| `expo-glass-effect` | **✗** | ✓(iOS26+) | **✗** | 平台字段只有 ios/tvos，非 iOS 回退普通 View |
| `@expo/ui` | ✓ | ✓ | **✗**（Jetpack Compose / SwiftUI 部分） | 平台字段 android/ios/tvos；只有 `Universal` 子集写了「run on Android, iOS, and web」 |
| `NativeTabs` | ✓ | ✓ | 降级实现 | 见 1.3 |

**这直接给出两条硬约束**：`expo-glass-effect` 与 `@expo/ui` 的 Compose/SwiftUI 组件**必须**用平台后缀隔离，
否则 Web 打包/渲染会出问题。

### 2.3 大屏 Web 的宽度约束

`MaxContentWidth`（=800）**不是 Expo API**，是 create-expo-app 模板自己的常量。
常见做法（社区经验 + 模板现状）：外层 `flexDirection:'row'` + `justifyContent:'center'`，
内层容器设 `maxWidth` 并 `alignSelf:'stretch'`；DAMN 的 `index.tsx` 与 `app-tabs.web.tsx` 已经在这么写。
Web 端顶部栏用 `position:'absolute'` + `maxWidth` 居中胶囊，也是模板现成做法，可直接复用。
注意 `MaxContentWidth: 800` 对宽屏偏窄 —— 窄屏/宽屏两档时建议给 Web 一个更大的容器上限（如 1024/1200），
但**这是设计决策，不是文档规定**。

---

## 3. 设计 token 分层架构

### 3.1 权威出处要说清楚（重要纠偏）

- [W3C Design Tokens Community Group — Design Tokens Format Module 2025.10](https://www.designtokens.org/tr/drafts/format/)
  定义的是**文件格式**：token = 带 `$value` 的对象、group、`$type`、别名（`{group.token}`）、`$extensions`。
  页面顶部红字警告「这是预览草稿，**不要直接引用或实现**」。**它没有规定 primitive/semantic/component 三层结构** ——
  这是业界惯例，不是规范。写成"W3C 规定了三层"是不准确的。
- 三层命名的权威出处（Salesforce Lightning、Nathan Curtis 的 token 命名文章等）**本次未核实**，不作为依据。
- **可核实且正好对口的正面例子**：Expo 官方博客
  [Nesting tabs and drawers with Expo Router](https://expo.dev/blog/nesting-tabs-and-drawers-with-expo) 第 5 节
  "Scalable theme architecture"，给了 `palette`（原始色值）→ `lightTheme/darkTheme.colors`（semantic：`background/surface/text/primary`）
  的两层 TS 落地代码，并指出这样能在嵌套导航边界上**同步应用主题、避免 FOUC**。
  DAMN 的 `Colors.light/dark` + `ThemeColor` 类型 + `ThemedView/ThemedText` 已经是这个形状。

### 3.2 Tailwind/NativeWind vs 纯 TS 常量

Expo 官方 [Tailwind CSS 指南](https://docs.expo.dev/guides/tailwind/) 开头就写：
**标准 Tailwind 只支持 Web；跨端要用 NativeWind 或 Uniwind**，并说 `web.bundler` 必须是 `metro`。

| 维度 | 纯 TS 常量（现状） | NativeWind v4 | react-native-unistyles v3 |
|---|---|---|---|
| 依赖/构建 | 0 | tailwindcss v3 + babel/metro 配置 | babel 插件 + `react-native-nitro-modules` + prebuild |
| 学习成本（0 React 基础） | 最低：就是对象 + `styles` | 中：要懂 Tailwind 类名体系 | 中高：`StyleSheet.create` 增强 + 变体/媒体查询 |
| 断点能力 | 自己写 `useWindowDimensions` | `sm: md: lg:` 前缀，**但官方文档自己 caution：默认断点是给 Web 设计的，不是给原生设计的** | 内置 breakpoints + media queries |
| 明暗主题 | `useColorScheme` + 两套对象 | `dark:` 前缀 / CSS 变量 | 主题对象 + 运行时切换 |
| 3 天工期风险 | **低** | 中（构建链一环出错就卡住） | 高（要求 New Arch、不支持 Expo Go、需 prebuild） |
| 包体积 | 最小 | 中（Tailwind runtime/css interop） | 中（nitro 原生模块） |

**推断**：DAMN 只有 5 个页面、0 React 基础、3 天，**引入任一 CSS 方案都是负收益**。NativeWind/Unistyles 的收益在
"几十上百个组件后的一致性"，而不是在 5 个页面。

### 3.3 明暗主题方案对比

| 方案 | 优点 | 代价 | 适合 DAMN？ |
|---|---|---|---|
| `useColorScheme` + 常量对象（现状） | 0 依赖、同步、SSR 友好、模板已铺好 `ThemedText/ThemedView` | 不能做"用户手动切换 light/dark/system"的持久化，除非自建 Context | ✅ 保持 |
| Context Provider + AsyncStorage | 支持手动三态切换 | 要写 Provider、持久化、避免 FOUC | 只有明确要"设置页切主题"才加 |
| NativeWind `dark:` / `colorScheme.set()` | 类名直接表达；`colorScheme.set()` 可手动切（[官方 Dark Mode 文档](https://www.nativewind.dev/docs/core-concepts/dark-mode)） | 引入整套构建链 | ❌ |
| unistyles v3 | 主题 + 断点 + 变体一体 | 强制新架构、需 prebuild、**不支持 Expo Go**（[官方 getting started](https://www.unistyl.es/v3/start/getting-started/)） | ❌ |

补充：Expo 官方 [Color themes](https://docs.expo.dev/develop/user-interface/color-themes/) 明确
`userInterfaceStyle: "automatic"`（DAMN 已设）是双端支持明暗的前提，Android 还需装 `expo-system-ui`（DAMN 已装）。
另外 `expo-router` 的 `ThemeProvider + DarkTheme/DefaultTheme`（DAMN `_layout.tsx` 已用，SDK 56+ 从 `expo-router` 导出）
是官方文档点名的**修复 iOS 26 切 tab 白闪 / liquid glass 闪烁**的手段 —— 现状已经修好了。

---

## 4. 断点与自适应

| 手段 | 说明 | 取舍 |
|---|---|---|
| `useWindowDimensions()` | RN 官方 hook，`{width, height, scale, fontScale}`，**窗口/字体缩放变化时自动重渲染**（[RN 文档](https://reactnative.dev/docs/usewindowdimensions)） | **首选**。无依赖、Web 上跟随浏览器窗口 |
| `Platform.OS` / `Platform.select` | 平台判断 | 表达"平台差异"而非"尺寸差异"，不要拿它做响应式 |
| `onLayout` | 测量**父容器**实际宽度 | 组件库级别才需要；页面级用 `useWindowDimensions` 更简单 |
| `react-native-responsive-*` 库 | 社区百分比换算 | 本次未核实其维护状态与 Web 行为，**不建议在 0 基础团队引入**；`useWindowDimensions` 已覆盖需求 |

**断点建议（移动优先 + Web 增强）**：

- **768px** —— 唯一有官方背书的分界点：React Navigation 官方文档的响应式侧栏示例用的就是 `width >= 768`。
- **1024px** —— 社区常见约定（对应 Tailwind `lg`），用于"是否加宽容器 / 是否两栏"。**这是社区经验，非文档规定**。
- DAMN 现在的 `MaxContentWidth: 800` 建议拆成两档：`<768` 用手机布局，`>=768` 用 `MaxContentWidth` 居中容器（可提升到 1024）。

落地形态（不需要新依赖）：
`const { width } = useWindowDimensions(); const wide = width >= 768;`
Web 侧栏 = 在 `app-tabs.web.tsx` 里把 `CustomTabList` 的 `flexDirection` 从 `'row'` 改成 `'column'` 并靠左，
内容区 `TabSlot` 用 `flexDirection: 'row'` 包一层 —— **只动一个文件的样式，不动路由**。

---

## 5. 最终结论：一套响应式代码，不拆两套布局

**推荐：一套响应式代码 + 保留现有「平台后缀导航壳」。**

理由：

1. **官方就是这么推荐的，而且 DAMN 已经这么做了。**
   [Native tabs 文档](https://docs.expo.dev/router/advanced/native-tabs/)的 "Custom web layout / Shared component with platform extensions"
   一节的示例文件名与 DAMN 的 `src/components/app-tabs.tsx` + `app-tabs.web.tsx` 完全对应。
   这条路的代价**已经沉没，边际成本接近 0**。
2. **5 个页面 / 3 天 / 0 React 基础 = 不能有第二套状态与第二套调试面。**
   独立 Web 控制台意味着：第二套导航、第二套主题接线、第二套 API 适配、双倍的真机 vs 浏览器差异排查。
   按第 1、2 节的限制清单（Android 5 tab 上限、NativeTabs Web 降级、glass-effect/@expo/ui 无 Web、
   reanimated Web 性能降低），任何一条都可能在最后一天变成阻塞项。
3. **"可能要在浏览器展示" ≠ 需要控制台。** 5 个页面 + `web.output: static` 已经能导出一个可分享的静态站点，
   做汇报演示完全够；控制台式的信息密度（表格、多栏、侧栏筛选）是另一套产品需求，不是"双端"的自然结果。

**代价与必须接受的现实：**

| 代价 | 应对 |
|---|---|
| Web 端观感 ≠ 原生观感（NativeTabs 在 Web 是降级实现） | Web 明确走 `app-tabs.web.tsx`（现状），把它当"演示壳"而非旗舰 |
| 需要为每个新页面做两遍导航登记（两处 Trigger/TabTrigger） | 抽一个 `TABS` 数组常量，两个壳都从它 map —— 5 个页面可控 |
| 图标要写 `{ios, android, web}` 三元组 | 已在做；统一封一个 `<AppIcon>` |
| `expo-glass-effect` / `@expo/ui` 无 Web | 必须平台后缀隔离；演示路径上干脆不用 |
| 长列表 Web/Native 滚动行为不同 | 容器统一 `maxWidth` + `ScrollView`，避免 `FlatList` 高级特性 |
| 真机 release 构建有 SDK 57 已知回归的传闻（[#47687](https://github.com/expo/expo/issues/47687)） | 提前用 preview 构建跑一次冒烟测试，别等到演示当天 |

**什么时候才该拆两套？** 只有当 Web 端出现"手机端不存在的角色/权限/数据视图"时
（例如管理员后台）。到那时再拆，而且是**新建一个独立的 Expo 项目**消费同一个后端，
而不是在同一个 `src/app/` 里塞两套布局 —— 后者会让 `typedRoutes`、深链、主题全部开始互相污染。
