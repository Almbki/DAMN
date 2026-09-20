import '@/global.css';

import { Platform } from 'react-native';

/**
 * DAMN design tokens.
 *
 * Identity: paper and hairlines (black / white / grey) with a single accent —
 * mint. Mint means "now" and nothing else: it marks the live segment on the
 * ruler, never decoration, never a second semantic colour. Completion and
 * secondary actions use ink or the hairline, not the accent.
 */

export const Palette = {
  light: {
    paper: '#FFFFFF',
    panel: '#FAFAFA',
    line: '#E7E7E7',
    lineStrong: '#111111',
    ink: '#111111',
    inkMuted: '#6B6B6B',
    inkFaint: '#9C9C9C',
    mint: '#10B981',
    mintInk: '#0B7A55',
    onInk: '#FFFFFF',
    hover: 'rgba(17,17,17,0.04)',
    pressed: 'rgba(17,17,17,0.08)',
  },
  dark: {
    paper: '#0D0D0D',
    panel: '#161616',
    line: '#2A2A2A',
    lineStrong: '#F2F2F2',
    ink: '#F2F2F2',
    inkMuted: '#A6A6A6',
    inkFaint: '#6E6E6E',
    mint: '#34D399',
    mintInk: '#6EE7B7',
    onInk: '#0D0D0D',
    hover: 'rgba(242,242,242,0.05)',
    pressed: 'rgba(242,242,242,0.09)',
  },
} as const;

export type ThemeName = keyof typeof Palette;
export type ThemeColorKey = keyof (typeof Palette)['light'];
export type ThemeColors = Record<ThemeColorKey, string>;

export const Space = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

export const Radius = {
  sm: 4,
  md: 8,
  pill: 999,
} as const;

/** One type scale for both ends: sizing does not change with width, density does. */
export const Type = {
  micro: 11,
  small: 12,
  body: 15,
  bodyLg: 16,
  title: 18,
  heading: 22,
  display: 84,
  displaySm: 56,
  unit: 26,
} as const;

export const Line = {
  tight: 1.3,
  normal: 1.5,
  relaxed: 1.6,
} as const;

export const Fonts = {
  mono: 'IBMPlexMono_500Medium',
  monoRegular: 'IBMPlexMono_400Regular',
  sans: Platform.OS === 'web' ? 'var(--font-sans)' : undefined,
};

export const Layout = {
  breakpoint: 768,
  sidebarWidth: 240,
  contentMax: 760,
  padWide: 32,
  padNarrow: 16,
  headerHeight: 64,
  navHeight: 60,
} as const;

export const Motion = {
  entrance: 240,
} as const;
