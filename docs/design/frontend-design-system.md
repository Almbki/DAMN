# 前端设计系统（Material 3 · 葱绿)

> 这是前端样式的唯一配置说明。**所有可调项都在 `frontend/src/constants/tokens.ts`**，
> 本文件是它的解释与约定。改样式先改 tokens，不要在组件里写死颜色/阴影/圆角。

- 方向：**Soft Instrument** —— Material 3 的结构，把彩度整体压低，阴影做成"软而实"
  （环境影 + 主影 + 顶部高光，按下转内凹）。界面像可以按的实物，不是扁平矩形。
- 主题：**目前只有浅色**。深色角色已在 tokens 里备好但未启用；以后加主题只需放开
  `state/theme.tsx`，组件的取色接口不变。
- 实现：Expo SDK 57 / react-native-web。不引入 MD 组件库，按 MD3 规范自建基元
  （`src/components/ui/*`），这样能守住上面的 RNW 约束与视觉身份。

---

## 1. 颜色

单一色种：**葱绿**。`PRIMARY_SEED = '#6FA33A'`。所有 primary / tertiary 角色都从它推导；
换主题色 = 改这个种子并重推下面两组值。

### 1.1 Material 3 角色（浅色，现行）

| 角色 | 值 | 用途 |
| --- | --- | --- |
| `primary` | `#417A34` | 主操作（填充按钮、进度、选中） |
| `onPrimary` | `#FFFFFF` | primary 上的文字 |
| `primaryContainer` | `#CBECC0` | 次级强调块（tonal 按钮、高亮行） |
| `onPrimaryContainer` | `#0E2A0A` | 容器上的文字 |
| `secondary` | `#5C7A58` | 辅助操作 |
| `secondaryContainer` | `#DCE8D6` | 辅助 chip/标签底 |
| `tertiary` | `#6FA33A` | **"现在"**（鲜活葱绿，唯一 live 色） |
| `tertiaryContainer` | `#DCF0CB` | "现在"的浅底 |
| `error` | `#A1514A` | 错误、逾期 |
| `background` / `surface` | `#F5F7F4` | 页面底（冷绿灰，避开奶油色套路） |
| `onSurface` | `#1A2118` | 主文字 |
| `onSurfaceVariant` | `#586152` | 次文字 |
| `surfaceContainerLowest` | `#FFFFFF` | 抬升卡片 |
| `surfaceContainerLow` | `#EEF2EC` | 凹陷/分组面 |
| `surfaceContainer` | `#E7EDE4` | 页头、栏底 |
| `surfaceContainerHigh` | `#DFE7DB` | 更强调的分组 |
| `outline` | `#7C877A` | 描边控件/输入框边框 |
| `outlineVariant` | `#C6CFC2` | 发丝分隔线 |
| `scrim` | `rgba(12,20,10,0.45)` | 弹层遮罩 |

深色角色见 `tokens.ts` 的 `Palette.dark`（暂不启用，值已配好）。

### 1.2 语义别名（组件直接用这些，避免角色名泄漏到业务）

`paper`(=surface) · `panel`(=surfaceContainerLow) · `line`(=outlineVariant) ·
`lineStrong`(=outline) · `ink`(=onSurface) · `inkMuted`(=onSurfaceVariant) ·
`inkFaint`(=outline) · `onInk`(=onPrimary) · `now`(=tertiary) · `nowContainer` ·
`onNow` · `hover` · `pressed` · `focusRing`。

### 1.3 用色规则

1. **只有 `now` 是 live 色**：当前任务、计时器进度、标尺当前刻度用它；别处一律中性。
2. 完成/次级动作走 ink 或容器色，**不借 now**。
3. 不做渐变装饰、不用彩色当背景块（容器色除外）。
4. 文本对比：正文 `onSurface`，次要 `onSurfaceVariant`；`onSurfaceVariant` 不用于 <14px 的密集数字。

---

## 2. 阴影 / 高程（微拟物核心）

`Elevation`（`tokens.ts`）是**跨端 CSS box-shadow 字符串**（RN 0.76+ 与 RNW 都支持）：

| 名 | 值 | 场景 |
| --- | --- | --- |
| `level0` | `none` | 平铺列表、页面底 |
| `level1` | `0 1px 2px rgba(26,40,24,.08), 0 1px 3px rgba(26,40,24,.06)` | 常驻卡片、chip |
| `level2` | `0 2px 4px .09, 0 4px 8px .07` | 抬升卡片、导航栏 |
| `level3` | `0 4px 8px .09, 0 8px 20px .09` | 弹窗、底部抽屉、FAB |
| `level4` | `0 6px 12px .10, 0 12px 28px .11` | 对话框 |
| `level5` | `0 8px 16px .12, 0 16px 36px .13` | 极少用（浮起拖拽） |
| `highlight` | `inset 0 1px 0 rgba(255,255,255,.7)` | 叠加在抬升面上做顶高光 |
| `inset` | `inset 0 1px 2px rgba(26,40,24,.12)` | 按下态（按钮、输入框、勾选） |

规则：
- 阴影用**绿调近黑** `rgba(26,40,24,·)`，不是中性黑 —— 这是"微拟物"的粘合点。
- 抬升面 = `levelN` **并且**（可选）叠加 `highlight`；按下 = 换成 `inset`，不用位移。
- 层级靠**阴影 + 容器色**双通道表达，不靠边框。
- **不要**给所有卡片同一个阴影：列表行 `level0`、常驻卡 `level1`、浮层 `level3+`。

---

## 3. 形状

`Radius`：`none 0 · xs 4 · sm 8 · md 12 · lg 16 · xl 28 · pill 999`。

按层级用，**不要所有东西同一个圆角**：
输入框 `xs` · chip/分段 `pill` · 按钮 `pill` · 卡片 `lg` · 底部抽屉顶角 `xl` · 对话框 `xl` · FAB `lg`。

---

## 4. 字体与字阶

两族：
- 正文/UI：系统 CJK 栈（`global.css` 的 `--font-sans`），权重 400 / 500 / 700。
- 数字：**IBM Plex Mono**（`Fonts.mono` / `monoRegular`）—— 时长、计数、时钟、比例。

MD3 字阶（`Type` + `LineHeight`）：

| token | size / line | 用途 |
| --- | --- | --- |
| `displaySmall` | 36 / 44 | 计时器、超大数字 |
| `headlineSmall` | 24 / 32 | 页面主标题 |
| `titleLarge` | 22 / 28 | 区块标题 |
| `titleMedium` | 16 / 24 | 卡片标题、按钮 |
| `titleSmall` | 14 / 20 | 列表主行 |
| `bodyLarge` | 16 / 26 | 正文 |
| `bodyMedium` | 14 / 22 | 次要正文 |
| `bodySmall` | 12 / 18 | 注释 |
| `labelLarge` | 14 / 20 | 按钮/标签 |
| `labelMedium` | 12 / 16 | chip、脚注 |

规则：数字一律 mono；正文行高 ≥1.6（CJK）；不用全大写 label；不做"某词变色"式强调。

---

## 5. 间距与布局

- `Space`：`xs 4 · sm 8 · md 12 · lg 16 · xl 24 · xxl 32 · xxxl 48`。
- `Layout`：断点 `840`；宽屏左侧 `railWidth 88`；窄屏底部 `navBarHeight 80`；
  内容列 `contentMax 880`；页边距宽 `32` / 窄 `16`。
- 宽屏：导航栏（rail）+ 单列内容，**左对齐**，正文 <80 字符。
- 窄屏：底部导航栏 + 全宽内容。
- 页面纵向节奏：区块间距 `xxl`，区块内 `md/lg`。

---

## 6. 状态层（MD3）

`StateLayer`：hover `.06` · focus `.12` · pressed `.12` · drag `.16`。
- 悬停/按下 = 在控件底色上叠一层 `onSurface`（浅色下即 `colors.hover` / `colors.pressed`）。
- 键盘焦点：外圈 `2px` `colors.focusRing`（= primary），始终可见。
- 禁用：`opacity .38`，不参与交互。

---

## 7. 按钮规格

`components/ui/button.tsx`，四种 variant，全部 `pill`、`minHeight 44`（触达）、
文字 `labelLarge / 500`。

| variant | 底 | 文 | 边框 | 阴影 | 用途 |
| --- | --- | --- | --- | --- | --- |
| `filled` | `primary` | `onPrimary` | 无 | `level1` | 每屏唯一主操作 |
| `tonal` | `primaryContainer` | `onPrimaryContainer` | 无 | `level1` | 次操作 |
| `outlined` | 透明 | `primary` | `1px outline` | 无 | 平级次操作 |
| `text` | 透明 | `primary` | 无 | 无 | 行内/第三级 |

状态：
- hover：统一叠 `StateLayer.hover` 中性层（filled 用 `onPrimary` 叠亮）。
- pressed：底不变，改叠 `pressed` 层并换 `Elevation.inset`（微拟物"按下去"）。
- focus：外圈 `2px focusRing`。
- disabled：`opacity .38`。

图标按钮同规格，`48×48` 或 `40×40`，`Radius.pill`。

---

## 8. 组件基元清单（`src/components/ui/`）

| 文件 | 说明 |
| --- | --- |
| `surface.tsx` | `Surface` = 容器 + `elevation` + `radius`，微拟物基底 |
| `icon.tsx` | 纯 View 画的几何图标（无图标字体依赖） |
| `button.tsx` | MD3 四变体按钮 / 图标按钮 |
| `segmented.tsx` | MD3 分段按钮（互斥选择） |
| `checkbox.tsx` | MD3 勾选（勾选即完成） |
| `progress.tsx` | MD3 线性进度 |
| `dialog.tsx` | MD3 基础对话框（确认类） |
| `bottom-sheet.tsx` | MD3 底部抽屉（反馈、变更、拆解） |
| `text-field.tsx` | MD3 描边输入框 |
| `states.tsx` | 空/错/加载态 |
| `chip.tsx` | 过滤 chip |
| `interaction.ts` | hover/focus/pressed 能力检测 |

---

## 9. 可访问性底线

- 所有可点元素有 `accessibilityRole` + label；键盘可达、焦点可见。
- `useReducedMotion()` 控制唯一入场动效；不散落 hover 动画。
- 正文对比 ≥4.5:1（上表值已按此选）；触达 ≥44px。
- 空/错状态说明"发生了什么 + 下一步"，不道歉、不模糊。
