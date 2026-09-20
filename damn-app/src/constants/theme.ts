/**
 * DAMN 设计系统 —— 唯一的设计 token 来源。
 *
 * ## 设计立场：这个产品卖的是「松一口气」，不是「加油」
 *
 * 效率类 App 普遍在做激励（红色倒计时、连胜火焰、鞭策式进度条）。
 * DAMN 的机制**恰好相反** —— 它把任务量往下调。所以视觉语言不该是「冲」，
 * 该是「轻」：不加压、不催促、不用饱和度抢注意力。
 *
 * 那条判断决定了本文件里所有取舍，改动前请先读这一节。
 *
 * ## 相对通用 AI 风格的有意偏离
 *
 * - 底是**冷灰白** `#F2F4F6`，不是暖米色 —— 暖米色是生成式设计的头号特征
 * - 暗色是 `#15171A`，不是近黑 `#0B0B0B`
 * - **不用卡片堆叠**：结构靠发丝线（rule），不靠一堆同圆角同阴影的圆角盒子
 * - 金色**只给「现在」这一件事**，绿色**只给「完成」**，其余保持中性
 * - 没有渐变、没有装饰性色块、没有编号徽章、没有全大写小标签
 *
 * ## 硬约束（改动前务必读）
 *
 * 1. 字重只用 400 / 700。安卓默认中文字体通常只有这两档，
 *    500/600 会被忽略或渲染成合成假粗体 → 层级靠字号 + 灰度，不要只押字重。
 * 2. 暗色不用纯黑，且**暗色下阴影基本不可见** → 一律用描边/发丝线表达边界。
 * 3. 组件不要写颜色字面量，一律从 Colors 取。
 * 4. **不要在浏览器上用 JS 动画驱动布局属性**（每帧触发回流会吃满主线程）。
 *    要动效优先用 CSS transition，且只动 transform / opacity。
 */

import '@/global.css';

import { Platform } from 'react-native';

/* ------------------------------------------------------------------ *
 * primitive —— 原始色值（组件请用下面的 Colors）
 * ------------------------------------------------------------------ */

export const Palette = {
  /* ---- 中性：更亮、更冷的纸与墨 ----
   * v2 调整：底从 #F2F4F6 提到 #F5F7FA，墨从 #16181C 压到 #12151B。
   * 目的是"年轻" —— 旧灰偏绿偏脏，压不住鲜艳的强调色。 */
  /** 纸 · 冷白页面底 */
  mist: '#F5F7FA',
  /** 抬升面用纯白 */
  haze: '#FFFFFF',
  /** 墨 · 正文与深底 */
  ink: '#12151B',
  /** 次要文字 —— 实测 5.57:1，过 AA */
  muted: '#5C6470',
  /** 最弱一级 —— **只允许非文字用途**（刻度、分隔线、未选中图标）。
   *  实测 3.39:1，用在正文上过不了 AA。 */
  faint: '#7E8794',
  /** 发丝线 */
  rule: '#E3E7ED',
  ruleFaint: '#EEF1F5',

  /* ---- 强调：琥珀 ----
   * v2 调整：旧金 #8A5A0B 偏棕、偏"皮革"，是显老的主因。
   * 现在拆成两个值：填充用更鲜的，文字用够对比度的。 */
  /** 「现在」的文字与线 —— 亮底上 4.25:1 */
  amberInk: '#A8670A',
  /** 「现在」的填充（按钮底）—— 配深墨字 */
  amberFill: '#C67C10',
  /** 选中态的极淡底 */
  amberWash: '#FBF0DC',

  /* ---- 完成：薄荷绿 ----
   * v2 调整：旧鼠尾草 #4A6B4F 灰而闷；换成更清亮的绿。 */
  /** 亮底上 4.4:1 */
  jadeInk: '#0E8A5F',
  jadeFill: '#0F9D63',
  jadeWash: '#E2F5EC',

  /** 危险 · 克制，不用纯红 */
  clay: '#C0392B',
  clayWash: '#FCEAE7',

  /* ---- 深色对应值 ---- */
  night: '#12141A',
  nightRaised: '#1A1D24',
  nightRule: '#262A33',
  nightRuleFaint: '#1F232A',
  nightInk: '#E9EDF2',
  nightMuted: '#99A3B0',
  nightFaint: '#6D7784',
  /** 暗底上的琥珀要提亮才鲜 */
  nightAmber: '#FFC24B',
  nightAmberWash: '#2E2718',
  /** 暗底上的薄荷 */
  nightJade: '#4ADE9B',
  nightJadeWash: '#16281F',
  nightClay: '#FF8A75',
  nightClayWash: '#2C1D1A',
} as const;

/**
 * 精力等级色阶。
 *
 * 用琥珀的**深浅**表达程度，不用红/黄/绿 —— 红黄绿会给用户压力感，
 * 而 DAMN 的目标是「无感完成」。每档都配了前景色，保证对比度。
 */
export const Levels = {
  light: {
    fills: ['#F0E3C8', '#E4C88C', '#D79E3C', '#A8670A'] as const,
    onLevels: ['#12151B', '#12151B', '#12151B', '#FFFFFF'] as const,
  },
  dark: {
    fills: ['#33291A', '#5A4622', '#9A7420', '#FFC24B'] as const,
    onLevels: ['#E9EDF2', '#E9EDF2', '#12141A', '#12141A'] as const,
  },
} as const;

/* ------------------------------------------------------------------ *
 * semantic —— 组件只用这一层
 * ------------------------------------------------------------------ */

export type ColorScheme = {
  /** 页面底 */
  bg: string;
  /** 次级底 / 抬升面 */
  raised: string;
  /** 主要文字 */
  text: string;
  /** 次要文字。**可达下限于此，正文不要更浅** */
  textMuted: string;
  /** 最弱一级。**仅非文字用途** —— 刻度、分隔线、未选中图标 */
  textFaint: string;
  /** 发丝线（结构的主角） */
  rule: string;
  /** 更弱的线 */
  ruleFaint: string;
  /** 「现在」的**文字与线**。只给「现在」 */
  accent: string;
  /** 「现在」的**填充**（按钮底）。与 `accent` 分开，因为两者的对比度要求不同 */
  accentFill: string;
  /** 强调色的浅底 */
  accentWash: string;
  /** 完成色的文字。**只给「完成」** */
  success: string;
  /** 完成色的填充 */
  successFill: string;
  successWash: string;
  /** 危险色。克制使用 */
  danger: string;
  dangerWash: string;
  /** 实心按钮／色块上的文字 */
  onAccent: string;
};

export const Colors: Record<'light' | 'dark', ColorScheme> = {
  light: {
    bg: Palette.mist,
    raised: Palette.haze,
    text: Palette.ink,
    textMuted: Palette.muted,
    textFaint: Palette.faint,
    rule: Palette.rule,
    ruleFaint: Palette.ruleFaint,
    accent: Palette.amberInk,
    accentFill: Palette.amberFill,
    accentWash: Palette.amberWash,
    success: Palette.jadeInk,
    successFill: Palette.jadeFill,
    successWash: Palette.jadeWash,
    danger: Palette.clay,
    dangerWash: Palette.clayWash,
    /* ⚠️ 浅色的琥珀填充上**用深墨字，不用白字** ——
       #FFFFFF on #C67C10 只有 3.34:1，深墨有 5.1:1。
       而且深字压在暖饱和色上比白字更"亮"、更年轻。 */
    onAccent: Palette.ink,
  },
  dark: {
    bg: Palette.night,
    raised: Palette.nightRaised,
    text: Palette.nightInk,
    textMuted: Palette.nightMuted,
    textFaint: Palette.nightFaint,
    rule: Palette.nightRule,
    ruleFaint: Palette.nightRuleFaint,
    accent: Palette.nightAmber,
    accentFill: Palette.nightAmber,
    accentWash: Palette.nightAmberWash,
    success: Palette.nightJade,
    successFill: Palette.nightJade,
    successWash: Palette.nightJadeWash,
    danger: Palette.nightClay,
    dangerWash: Palette.nightClayWash,
    onAccent: Palette.night,
  },
};

/** 语义色名。`ThemedText themeColor=` / `ThemedView type=` 接受这些 key。 */
export type ThemeColor = keyof ColorScheme;

/* ------------------------------------------------------------------ *
 * 字体
 * ------------------------------------------------------------------ */

/**
 * 中文在 RN 里**不要用自定义字体** —— 中文字体动辄好几 MB，
 * 而且混排时字形与基线会和拉丁字体打架。
 * 所以：中文一律走系统字体；只给**拉丁字母与数字**加一个衬线字，
 * 用在时间、数字、以及页面的大标题句子上。
 *
 * `serif` 在原生上是平台衬线，在 Web 上由 `global.css` 指向 Newsreader。
 */
export const Fonts = Platform.select({
  ios: {
    sans: 'system-ui',
    serif: 'ui-serif',
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    mono: 'monospace',
  },
  web: {
    sans: 'var(--font-sans)',
    serif: 'var(--font-serif)',
    mono: 'var(--font-mono)',
  },
});

/**
 * 字阶。
 *
 * 两件事要注意：
 * - **中文不要用负向 letterSpacing**（那是给拉丁字母的），标题一律 `0`
 * - 字重只有 400 / 700 可用（见文件顶部硬约束）
 *
 * `serif` 只作用在拉丁字形上；中文会自动回退系统字体，这是预期行为。
 */
export const TypeScale = {
  /** 页面主标题（一句话，不是标签） */
  display: { fontSize: 30, lineHeight: 40, fontWeight: '400' },
  /** 时间/数字的主视觉 —— 拉丁衬线在这里最有表现力 */
  numeral: { fontSize: 56, lineHeight: 60, fontWeight: '400' },
  numeralSmall: { fontSize: 32, lineHeight: 36, fontWeight: '400' },
  /** 区块标题 */
  title: { fontSize: 22, lineHeight: 32, fontWeight: '400' },
  /** 任务名 */
  headline: { fontSize: 24, lineHeight: 36, fontWeight: '700' },
  subtitle: { fontSize: 17, lineHeight: 26, fontWeight: '700' },
  body: { fontSize: 16, lineHeight: 26, fontWeight: '400' },
  bodyBold: { fontSize: 16, lineHeight: 26, fontWeight: '700' },
  /** 次要说明 */
  small: { fontSize: 14, lineHeight: 22, fontWeight: '400' },
  smallBold: { fontSize: 14, lineHeight: 22, fontWeight: '700' },
  caption: { fontSize: 13, lineHeight: 20, fontWeight: '400' },
  /** 最小一级，只用于时间戳之类 */
  micro: { fontSize: 11, lineHeight: 16, fontWeight: '400' },
} as const;

export type ThemeType = keyof typeof TypeScale;

/* ------------------------------------------------------------------ *
 * 尺度
 * ------------------------------------------------------------------ */

/** 4pt 基数、8pt 主步进。不要混入 5 的倍数体系。 */
export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 12,
  four: 16,
  five: 24,
  six: 32,
  seven: 48,
  eight: 64,
} as const;

/**
 * 圆角刻意**偏小**：结构由发丝线负责，不是靠圆角盒子。
 * 大圆角 + 同质卡片是生成式设计最典型的形状语言。
 */
export const Radius = {
  sm: 4,
  md: 8,
  lg: 12,
  full: 999,
} as const;

/** 命中区下限（Apple 官方 44×44pt）。可点元素 minHeight 不要低于这个。 */
export const MinTouchTarget = 44;

/**
 * 状态层：交互态用叠加透明度，不换填充色。
 * 暗色下阴影不可见，所以边界一律用发丝线表达。
 */
export const StateLayer = {
  hover: 0.06,
  pressed: 0.12,
} as const;

/** 动效：120–300ms / ease-out。超过 300ms 会显得拖沓。 */
export const Motion = {
  fast: 120,
  base: 180,
  slow: 260,
} as const;

/* ------------------------------------------------------------------ *
 * 响应式：窄屏底栏 / 宽屏侧栏
 * ------------------------------------------------------------------ */

/**
 * 768 有官方背书 —— React Navigation bottom-tabs 文档的 `tabBarPosition`
 * 示例就是 `width >= 768 ? 'left' : 'bottom'`。
 */
export const Breakpoints = {
  /** 宽于此值：导航从底栏切到左侧栏 */
  sidebar: 768,
  /** 宽于此值：内容可加宽 */
  wide: 1100,
} as const;

/** 导航壳里按宽度切换布局用这个，别在组件里散落魔法数字。 */
export function navMode(width: number): 'bottom' | 'sidebar' {
  return width >= Breakpoints.sidebar ? 'sidebar' : 'bottom';
}

/** 正文最大宽度：守住「一行不超过 80 字符」这条排版底线。 */
export const MaxContentWidth = 640;
export const MaxContentWidthWide = 760;

/** 宽屏侧栏宽度 */
export const SidebarWidth = 208;
