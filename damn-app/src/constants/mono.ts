/**
 * 极简黑白设计 token —— 新前端的唯一视觉来源。
 *
 * ## 和 `theme.ts` 的关系
 *
 * `theme.ts` 是上一版（琥珀 + 薄荷、轻拟物）的设计系统，现在应用层不再使用，
 * 但 `error-boundary.tsx` 仍引用它的 `Colors`。这一版把视觉换成**纯黑白**：
 *
 * - 没有强调色，唯一的「重」是墨黑（`strong`）与它的反相；
 * - 结构靠 1px 边框和灰度，不靠阴影、不靠大圆角；
 * - 交互态用灰度底（hover / active），不换色相。
 *
 * ## 深浅双色
 *
 * 单色系可以安全反相：浅色是白底黑字，深色是黑底白字。
 * 深色不是纯黑（`#0E0E0E`），避免 OLED 上边界糊掉。
 */

import { Platform } from 'react-native';

export const MonoPalette = {
  light: {
    /** 页面底 */
    bg: '#FFFFFF',
    /** 侧栏 / 抬升面 */
    panel: '#FAFAFA',
    /** 悬停叠层 */
    hover: '#F0F0F0',
    /** 选中 / 当前项 */
    active: '#E5E5E5',
    /** 主要文字 */
    text: '#111111',
    /** 次要文字 */
    sub: '#666666',
    /** 最弱文字（仅非关键信息） */
    faint: '#999999',
    /** 发丝线 / 边框 */
    border: '#E5E5E5',
    /** 重色：实心按钮底、选中框、当前任务边框 */
    strong: '#111111',
    /** 重色上的文字 */
    onStrong: '#FFFFFF',
    /** 错误 */
    danger: '#B3261E',
    /** 输入 / 分区浅底 */
    wash: '#F7F7F7',
  },
  dark: {
    bg: '#0E0E0E',
    panel: '#161616',
    hover: '#1E1E1E',
    active: '#2A2A2A',
    text: '#F2F2F2',
    sub: '#A6A6A6',
    faint: '#787878',
    border: '#2A2A2A',
    strong: '#F2F2F2',
    onStrong: '#0E0E0E',
    danger: '#F2B8B5',
    wash: '#141414',
  },
} as const;

export type MonoColors = { [K in keyof (typeof MonoPalette)['light']]: string };
export type MonoColorName = keyof MonoColors;

/** 4pt 基数。 */
export const MonoSpace = {
  one: 4,
  two: 8,
  three: 12,
  four: 16,
  five: 24,
  six: 32,
  seven: 48,
} as const;

/** 圆角刻意偏小 —— 模板就是 4 / 8。 */
export const MonoRadius = {
  sm: 4,
  md: 8,
  full: 999,
} as const;

/**
 * 字阶。
 *
 * ⚠️ 字重只用 400 / 700：安卓默认中文字体通常只有这两档，
 * 500 / 600 会被忽略或渲染成合成假粗体。层级靠字号 + 灰度。
 */
export const MonoType = {
  logo: { fontSize: 18, lineHeight: 24, fontWeight: '700', letterSpacing: 1 },
  display: { fontSize: 20, lineHeight: 28, fontWeight: '700' },
  title: { fontSize: 15, lineHeight: 22, fontWeight: '700' },
  label: { fontSize: 12, lineHeight: 16, fontWeight: '700', letterSpacing: 0.5 },
  body: { fontSize: 14, lineHeight: 22, fontWeight: '400' },
  bodyStrong: { fontSize: 14, lineHeight: 22, fontWeight: '700' },
  sub: { fontSize: 13, lineHeight: 20, fontWeight: '400' },
  caption: { fontSize: 12, lineHeight: 18, fontWeight: '400' },
  micro: { fontSize: 11, lineHeight: 16, fontWeight: '400' },
} as const satisfies Record<string, import('react-native').TextStyle>;

export type MonoTypeName = keyof typeof MonoType;

/** 中文一律系统字体；拉丁与数字沿用 global.css 里的变量。 */
export const MonoFonts =
  Platform.select({
    web: { sans: 'var(--font-sans)', serif: 'var(--font-serif)' },
    default: { sans: 'normal', serif: 'serif' },
  }) ?? { sans: 'normal', serif: 'serif' };

/** 宽于此值：导航从底栏切到左侧栏。与 `theme.ts` 的 `Breakpoints.sidebar` 一致。 */
export const MonoBreakpoint = 768;
