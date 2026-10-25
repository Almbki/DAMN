# 跨平台 App 视觉设计系统与风格流派调研

> 对象：DAMN（AI 目标拆解 + 精力管理）· Expo SDK 57 / RN 0.86 / TS · 需明暗双主题。
> 【官方】=官方文档/仓库原文；【推断】=我的判断或社区经验；【未核实】=没找到权威来源，不编造。

## 一、主流设计系统

| 系统 | 官方入口 | 核心特征 | RN 适配 |
|---|---|---|---|
| Material Design 3 | [m3.material.io](https://m3.material.io/) · [色彩](https://m3.material.io/styles/color/system/overview) · [圆角](https://m3.material.io/styles/shape/corner-radius-scale) | **角色制**：组件只引用 `primary / on-primary / surface-container-*` 语义角色；HCT 生成 tonal palette；按压用**状态层**而非换填充 | 无官方 RN 实现，token 可直接抄 |
| Apple HIG | [HIG](https://developer.apple.com/design/human-interface-guidelines/) · [Typography](https://developer.apple.com/design/human-interface-guidelines/typography) · [Dos & Don'ts](https://developer.apple.com/design/tips/) | 【官方】命中区 ≥ **44×44pt**、文字 ≥ **11pt**；SF Pro + Dynamic Type | `safe-area-context` + `allowFontScaling` |
| Ant Design Mobile | [RN 文档](https://rn.mobile.ant.design/index-cn) · [token 源码](https://github.com/ant-design/ant-design-mobile-rn/blob/master/components/style/themes/default.tsx) | 中文语境最熟：14 基准字号、`#f5f5f9` 底、`#108ee9` 品牌蓝 | **有官方 RN 组件库** |
| Radix Colors | [色阶用法](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale) | 【官方】每色阶 **12 步、每步绑定用途**（1-2 背景 / 3-5 组件态 / 6-8 描边 / 9-10 实心 / 11-12 文字） | 纯 hex，直接抄 |
| Tailwind / NativeWind | [Tailwind Dark](https://tailwindcss.com/docs/dark-mode) · [NativeWind v5](https://www.nativewind.dev/v5/core-concepts/dark-mode) | 【官方】v5 把 `dark:` 映射到 `prefers-color-scheme`，**`:root.dark` 会被原生编译器拒绝**；切主题用 `Appearance.setColorScheme()`，v5 废弃了 nativewind 的 `useColorScheme()` | 支持 Expo 57 |
| Tamagui | [Themes](https://tamagui.dev/docs/intro/themes) · [Expo](https://tamagui.dev/docs/guides/expo) | 主题=变量、可嵌套 sub-theme（`dark_green_subtle`），缺 key 向上回退 token；内置 `background/color/borderColor` + Hover/Press/Focus 变体 | 支持 RN + Web |
| Gluestack UI | [文档](https://gluestack.io/ui/docs/home/getting-started/installation) · [仓库](https://github.com/gluestack/gluestack-ui) | 【官方】v5 基于 **NativeWind v5 / Tailwind v4**，copy-paste 非黑盒，Expo Router first | 支持 |
| shadcn 移植 | [React Native Reusables](https://reactnativereusables.com/docs) · [仓库](https://github.com/founded-labs/react-native-reusables) | shadcn/ui 的 RN 版，基于 NativeWind | 支持 RN/Web |
| Radix Primitives | [讨论 #1965](https://github.com/radix-ui/primitives/discussions/1965) | 【推断】只服务 Web DOM，**无原生 RN 实现**，只能抄设计语言 | — |

**任务/生产力类现成参考**：GSD Task Manager 的 [`DESIGN.md`](https://github.com/vscarpenter/gsd-task-manager/blob/feat/builder-gate1/DESIGN.md) —— 艾森豪威尔矩阵任务 App 的完整设计系统（YAML token + 设计理由 + Do/Don't），最贴近本产品形态的公开范例。

## 二、三套可直接抄的配色

### 方案 A：Material 3 baseline（紫 · 最省事，官方 Kit token）

来源 [Fluent-Qt 对照文档](https://github.com/calvinhxx/Fluent-Qt/blob/f41ba16a11397e9c911fc21431ec42e65e6b96be/docs/design-languages/material-3.md)（tonal 锚点 Primary40 `#6750A4` / Primary80 `#D0BCFF`）。

| 角色 | Light | Dark |
|---|---|---|
| Primary / On Primary | `#6750A4` / `#FFFFFF` | `#D0BCFF` / `#381E72` |
| Primary Container / On | `#EADDFF` / `#4F378A` | `#4F378B` / `#EADDFF` |
| Secondary / Container | `#625B71` / `#E8DEF8` | `#CCC2DC` / `#4A4458` |
| Tertiary / Container | `#7D5260` / `#FFD8E4` | `#EFB8C8` / `#633B48` |
| Error / Container | `#B3261E` / `#F9DEDC` | `#F2B8B5` / `#8C1D18` |
| Surface（页面底） | `#FEF7FF` | `#141218` |
| Surface Container Low/·/High/Highest | `#F7F2FA`/`#F3EDF7`/`#ECE6F0`/`#E6E0E9` | `#1D1B20`/`#211F26`/`#2B2930`/`#36343B` |
| On Surface / Variant | `#1D1B20` / `#49454F` | `#E6E0E9` / `#CAC4D0` |
| Outline / Variant | `#79747E` / `#CAC4D0` | `#938F99` / `#49454F` |

> 坑：`On Primary Container` 新版 `#4F378A`（旧资料 `#21005D`）；暗色 Surface 新版 `#141218`（旧版 `#1C1B1F`）。抄哪套要统一。

### 方案 B：Radix Violet + Slate（紫 + 中性 · 明暗自成体系）

来源 `@radix-ui/colors@3.0.0`：[violet](https://unpkg.com/@radix-ui/colors@3.0.0/violet.css) · [violet-dark](https://unpkg.com/@radix-ui/colors@3.0.0/violet-dark.css) · [slate](https://unpkg.com/@radix-ui/colors@3.0.0/slate.css) · [slate-dark](https://unpkg.com/@radix-ui/colors@3.0.0/slate-dark.css)

| 用途（步号） | Violet L | Violet D | Slate L | Slate D |
|---|---|---|---|---|
| 1 页面底 | `#fdfcfe` | `#14121f` | `#fcfcfd` | `#111113` |
| 2 次级底 | `#faf8ff` | `#1b1525` | `#f9f9fb` | `#18191b` |
| 3 卡片/组件底 | `#f4f0fe` | `#291f43` | `#f0f0f3` | `#212225` |
| 5 选中态 | `#e1d9ff` | `#3c2e69` | `#e0e1e6` | `#2e3135` |
| 6 细分隔线 | `#d4cafe` | `#473876` | `#d9d9e0` | `#363a3f` |
| 8 描边/焦点环 | `#aa99ec` | `#6958ad` | `#b9bbc6` | `#5a6169` |
| 9 实心主色 | `#6e56cf` | `#6e56cf` | `#8b8d98` | `#696e77` |
| 11 次要文字 | `#6550b9` | `#baa7ff` | `#60646c` | `#b0b4ba` |
| 12 主要文字 | `#2f265f` | `#e2ddfe` | `#1c2024` | `#edeef0` |

语义色（同源官方 CSS，浅底用 3 号 / 实心用 9 号 / 文字用 11 号）：成功 Grass `#46a758`（暗 `#71d083`，底 `#e9f6e9`/`#1b2a1e`）；警告 Amber `#ffc53d`（文字 `#ab6400`，暗 `#ffca16`）；危险 Red `#e5484d`（文字 `#ce2c31`，暗 `#ff9592`）。
> 【官方】Amber/Sky/Lime/Mint/Yellow 的 9 号是给**深色文字**设计的，警告色实心按钮上别用白字。

### 方案 C：GSD "Indigo & Cloud"（任务管理专用）

来源 [DESIGN.md](https://github.com/vscarpenter/gsd-task-manager/blob/feat/builder-gate1/DESIGN.md)。

| 角色 | 值 | 角色 | 值 |
|---|---|---|---|
| 页面底 Cool Stone | `#F4F4F0` | 主文 Ink Slate | `#13141B` |
| 卡片面 Cloud White | `#FFFFFF` | 次要文字（AA 下限） | `#6F6F75` |
| 主色 Deep Indigo / 按下 | `#3B4A8C` / `#2A3768` | 细描边 | `#CFCFCC` |
| 成功 Sage | `#788C5D` | 三级面 Oat | `#DDDCDF` |
| 危险 Rust / 按下 | `#B04A3F` / `#9A3F3F` | 灰阶 | `#EDEDEA`/`#CFCFCC`/`#6F6F75`/`#3A3B41` |
| 警告 Amber / 文字 | `#C78E3F` / `#A06A2A` | 暗色主色提亮 | `#7A8AD1` |
| 信息 Slate Blue | `#5C7CA3` | | |

> 该文档**暗色只给规则不给全 hex**，不能整表照抄；价值在**设计判断**。

## 三、排版与尺度

### 字号层级（M3 官方 type scale ↔ AntD Mobile RN token）

| 层级 | M3 官方 size/line/weight/tracking | AntD RN |
|---|---|---|
| Display Large | 57 / 64 / 400 / -0.25 | — |
| Headline Medium | 28 / 36 / 400 / 0 | `font_size_heading` 17 |
| Title Medium | 16 / 24 / **500** / 0.15 | `font_size_caption` 16 |
| Body Medium | 14 / 20 / 400 / 0.25 | `font_size_base` 14 |
| Label Large（按钮） | 14 / 20 / 500 / 0.1 | 按钮 18，主按钮高 47 |
| Label Small | 11 / 16 / 500 / 0.5 | `font_size_caption_sm` 12 |

- 【官方】GSD 字阶（消费级参考）：display 48/1.1 · headline 32/1.2 · title 19/1.22 · body 16/1.55 · label（等宽大写）11/1.0/字距 0.12em。
- 【推断】移动端建议：`display 32 / title 24 / headline 20 / body 16 / caption 13 / micro 11`，行高 = 字号×1.4~1.55，正文 16 起、最小 11。
- 【推断】中文别照抄 M3 的负向 letter-spacing（那是给拉丁字母的），标题建议 `letter-spacing: 0`。

### 圆角 / 间距 / 命中区

| 项 | 【官方】值 | 【推断】DAMN 建议 |
|---|---|---|
| 圆角 | M3：0/4/8/12/16/**28**/full；GSD：4/8/12/14/20/999；AntD：2/3/5/7 | 卡片 16、按钮 12（或 pill）、输入框 12、抽屉 28、chip pill |
| 组件尺寸 | M3 按钮高 40、Switch 52×32、Checkbox 18（r=2）、Radio 20、日期格 40 | 按钮 44（含热区） |
| 状态层 | M3：hover 8% / focus 10% / pressed 10% / dragged 16% | 直接复用 |
| 间距 | AntD 是 5 的倍数（3/6/9/15/21） | **4pt 基数、8pt 主步进**（4/8/12/16/24/32/48） |
| 命中区 | Apple：≥44×44pt；文字 ≥11pt | `minHeight: 44~48` |

> Android 的 48dp 命中区习惯值：【**未核实**】—— 没能取得官方原句，别当官方引文。

## 四、2024–2026 趋势：耐看 vs 速朽

| 做法 | 依据 | 判定 |
|---|---|---|
| 暗色用**深灰**而非纯黑 | Radix 暗色 1 号 `#111113`/`#14121f`、M3 暗色 Surface `#141218` —— 主流系统都不用 `#000000` | ✅ 耐看 |
| 暗色靠 `surface-container` 分层表达高度 | 【官方】M3 共五档 surface | ✅ 耐看 |
| **描边 > 阴影** | 【官方】GSD：hairline 是签名，静止态扁平、阴影只表示状态；M3 菜单/弹窗用 elevation 但无边框 | ✅ 耐看 |
| 大圆角 16–28 | 【官方】M3 xl=28 用于 dialog | ✅ 耐看 |
| 渐变 | 【官方】GSD 黑名单："no purple gradients, no gradient text" | ⚠️ 慎用，装饰渐变易土 |
| **玻璃拟态** | 【官方】`expo-glass-effect` 的 `GlassView` **仅 iOS 26+**（其他平台回退普通 View）；`expo-blur` 在 Android 需 `BlurTargetView` + `blurMethod='dimezisBlurViewSdk31Plus'`，SDK 31 以下走 RenderScript "much less efficient" | ⚠️ 锦上添花，不能当默认底 |
| 动效 120–300ms / ease-out / 尊重 `prefers-reduced-motion` | 【官方】GSD | ✅ 耐看 |
| 全屏渐变 hero / 渐变文字 / 800 超粗字重 / 大面积重阴影 | — | ❌ 一年就土 |

【推断】RN 落地：玻璃抽成 `GlassSurface` —— iOS 且 `isLiquidGlassAvailable()` 才用 `GlassView`，否则退化为 `rgba(255,255,255,0.72)` + hairline。

## 五、反例与坑

**1. B2B 控制台（如 open.bigmodel.cn）搬到消费 App**
- 侧栏 + 表格 + 密集数字：手机宽仅 360–430pt，侧栏必须变底部 Tab/抽屉，表格必须退化成卡片列表。
- 【官方】GSD 把这条路列为反面："**Don't** build a dense enterprise PM tool: no overwhelming toolbars, no deeply nested settings, no feature soup"；"**Don't** fall into the generic SaaS dashboard: no hero-metric template (big number + small label + gradient accent)"。
- 多色状态标签：控制台里低风险（专业用户看报表），消费 App 里每个任务挂 3 个彩色 chip 立刻像内部工具。GSD 对策：颜色永远配文字+位置，不靠颜色单独表意。
- 【官方】GSD "One Accent Rule"：强调色只花在意图上（主操作/选中/焦点/链接），**占屏面 ≤10%**。
- 【推断】对 DAMN：抄控制台的**纪律**（token 化、语义色、状态齐全），别抄**信息密度与布局骨架**。

**2. 暗色在 OLED / 低端安卓**
- 纯黑省电但放大黑位断层/拖影，且阴影完全不可见 —— 【官方】GSD 因此把暗色阴影改成 `rgba(0,0,0,0.45–0.55)`，理由"暖色低透明度阴影在暗面上会消失"。【推断/社区经验】"纯黑导致 banding/smearing"**未找到一手官方条文，未核实**。
- 【官方】expo-blur 的 Android 性能警告是真实机型差异，低端机模糊层掉帧；【推断】暗色下避免大面积半透明叠层（额外 overdraw），改用实色 token。

**3. 中文字体在 RN**
- **字重缺失（最大坑）**：Android 默认中文字体通常只有 Regular/Bold，`fontWeight: '500'/'600'` 被忽略或渲染成合成粗体。【推断/社区经验】，**未核实**。对策：只用 400/700，或自带字体文件。
- 自定义拉丁字体无中文字形 → 中文回退系统字体，混排字面/基线不一致。【推断】对策：`fontFamily` 只设在纯英文/数字的 `Text` 上。
- 官方 issue：[react-native#50137](https://github.com/facebook/react-native/issues/50137)（Android TextInput 占位符不遵守自定义字重）、[expo/expo#33673](https://github.com/expo/expo/issues/33673)（expo-font 在 Android 不生效）。
- **不要关字体缩放**：【官方】Appt 指南明确 `Text.defaultProps.allowFontScaling = false` 是 "accessibility anti-pattern"，应回滚（[来源](https://github.com/appt-org/appt-samples/blob/main/data/en/text-scale/react-native.md)）。中文长文案在大字模式下会撑爆固定高度卡片 → 卡片用 `minHeight`。
- 【推断】`letter-spacing` 对中文无收益。

## 六、结论：只能选一套 → **M3 角色骨架 + Radix Violet/Slate 色值**

```ts
type Scheme = {
  bg: string; bgSubtle: string; card: string; cardHi: string;
  border: string; borderStrong: string;
  text: string; textMuted: string; textFaint: string;
  primary: string; primaryPress: string; onPrimary: string; primarySoft: string;
  success: string; warning: string; danger: string;
};
```

1. **双主题成本最低**：M3 的角色制天生为明暗两套 scheme 设计，RN 侧只要两个 `Scheme` 对象 + 一个 `useColorScheme()` Context，不必在组件里写 `dark:` 分支；Radix 12 步同理。
2. **色值有官方背书、可直接粘**：M3 baseline 与 Radix 的 hex 都能给出处；相比 GSD 暗色不全、AntD 品牌蓝偏旧、Tailwind 默认色板偏 Web。
3. **气质对得上**：单主色 + 6 级 surface + 三语义色，刚好够表达「目标 / 子任务 / 精力等级 / 完成状态」；精力值这种连续量用 primary 的 tonal 深浅（Violet 3/6/9/12）比红黄绿更克制。
4. **落地摩擦最小**：不引入 Tamagui/Gluestack（多一层抽象，Expo 57 + RN 0.86 兼容要自己扛），自建 `theme.ts` + `StyleSheet` 足够；若要组件库选 **React Native Reusables**。
5. **明确不做**：玻璃拟态不当主视觉、渐变标题不要、侧栏+表格多色 chip 不要、暗底不用纯 `#000`。

**唯一要补的**：暗色下阴影换成 `rgba(0,0,0,0.45~0.55)` 或去掉改描边；**静止态扁平，只有交互态才抬升**（M3 未覆盖，取 GSD 规则）。
