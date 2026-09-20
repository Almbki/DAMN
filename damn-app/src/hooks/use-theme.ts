/**
 * 明暗主题与响应式工具。
 *
 * 用 `useTheme()` 取语义色 —— 组件里**不要**写 `dark:` 分支，
 * 也**不要**写颜色字面量；换主题时组件代码零改动。
 */

import { useEffect, useState } from 'react';
import { useWindowDimensions } from 'react-native';

import {
  Breakpoints,
  Colors,
  Fonts,
  Radius,
  Spacing,
  StateLayer,
  TypeScale,
  navMode,
  type ColorScheme,
  type ThemeType,
} from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { useThemeModeSafe } from '@/hooks/use-theme-mode';

export type Theme = ColorScheme;

/** 当前颜色方案（'light' | 'dark'）。
 *
 * **优先读手动切换的结果**（`ThemeModeProvider`），没有 Provider 时退回系统值。
 * 组件用它就同时支持"跟系统"和"手动切换"两件事，不需要知道当前是哪种。
 *
 * ⚠️ 必须把 `'unspecified'`（以及历史实现里的 null / undefined）归一成 `'light'` ——
 * `useColorScheme()` 的返回类型是 `ColorSchemeName = 'light' | 'dark' | 'unspecified'`，
 * 直接当 `'light' | 'dark'` 用会漏掉这一支。
 */
export function useScheme(): 'light' | 'dark' {
  const manual = useThemeModeSafe();
  const system = useColorScheme();
  if (manual) return manual.scheme;
  return system === 'dark' ? 'dark' : 'light';
}

/** 语义色。 */
export function useTheme(): Theme {
  return Colors[useScheme()];
}

/** 字号样式。用法：`const t = useType(); <Text style={t.title}>` */
export function useType(): typeof TypeScale {
  return TypeScale;
}

export type { ThemeType };

/**
 * 衬线族。
 *
 * 只作用在**拉丁字母与数字**上（时间、时长、大标题里的西文）；
 * 中文会自动回退系统字体 —— 这是刻意的，见 `constants/theme.ts` 的说明。
 */
export function useSerif() {
  return Fonts.serif;
}

/**
 * 数字排版：等宽数字 + 衬线 + 大字号。
 *
 * 为什么单独抽出来：时间与时长是这一版设计的**主视觉**，
 * 而且数字必须逐位对齐，否则数字变化时整行会左右抖。
 */
export function useNumeralStyle() {
  return {
    fontFamily: Fonts.serif,
    fontVariant: ['tabular-nums'] as const,
  };
}

/**
 * 响应式：窄屏底栏 / 宽屏侧栏。
 * 断点依据见 `constants/theme.ts` 的 `Breakpoints` 注释。
 */
export function useResponsive() {
  const { width, height, fontScale } = useWindowDimensions();

  return {
    width,
    height,
    /** 用户把系统字号调大了多少倍。容器要用 minHeight，避免被撑爆。 */
    fontScale,
    isWide: width >= Breakpoints.sidebar,
    isExtraWide: width >= Breakpoints.wide,
    mode: navMode(width),
  };
}

/** 需要尺寸/圆角常量时用它，省得到处 import。 */
export function useTokens() {
  return { Spacing, Radius, StateLayer };
}

/**
 * 是否已完成客户端挂载。
 *
 * 用途：静态渲染（SSR）阶段没有真实窗口尺寸 —— `react-native-web` 的
 * `Dimensions` 默认是 `width: 0`。如果首帧就用实际宽度决定布局，
 * **服务端与客户端会渲染出不同的 DOM 结构，导致 hydration 崩溃**，
 * 表现就是界面停在某一帧不动（「卡住」）。
 *
 * 所以第一帧统一按窄屏渲染，挂载后再切到真实宽度。
 */
export function useIsHydrated(): boolean {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  return hydrated;
}

/**
 * 是否宽屏（要切成侧栏）。
 *
 * ⚠️ 静态渲染阶段强制返回 `false`（窄屏），原因见 `useIsHydrated` ——
 * 这是修 hydration 崩溃的关键，别为了「首屏就出侧栏」把这个默认值改掉。
 */
export function useIsWide(): boolean {
  const hydrated = useIsHydrated();
  const { width } = useWindowDimensions();
  return hydrated && width >= Breakpoints.sidebar;
}
