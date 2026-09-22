import '@/global.css';

import { Platform } from 'react-native';

/**
 * DAMN design tokens.
 *
 * Direction: "Soft Instrument" — Material 3 structure with the chroma pulled
 * down and shadows made soft-but-physical (ambient + key + top highlight,
 * inset on press). The palette is generated from a single seed — scallion green
 * (葱绿). Change `PRIMARY_SEED` and re-derive the primary roles; nothing else
 * hard-codes the hue.
 *
 * Identity rules:
 *  1. One live colour — the vivid scallion `now`/`tertiary` tone — means
 *     "now" and nothing else. It marks the current task, the timer and the
 *     live ruler tick. Completion and secondary actions use ink or the
 *     neutral container tones, never the live colour.
 *  2. Every raised surface carries elevation (soft shadow + top highlight) and
 *     every pressed surface goes inset. This is the micro-skeuomorphic rule.
 *  3. Numbers are instruments: durations, counts and clocks use IBM Plex Mono.
 *
 * Light only for now; the dark roles are kept (unused) so the theme can be
 * switched on later without re-deriving. See docs/design/frontend-design-system.md.
 */

/** The one colour the whole palette is derived from. */
export const PRIMARY_SEED = '#6FA33A';

export const Palette = {
  light: {
    // ---- Material 3 colour roles ----
    primary: '#417A34',
    onPrimary: '#FFFFFF',
    primaryContainer: '#CBECC0',
    onPrimaryContainer: '#0E2A0A',
    secondary: '#5C7A58',
    onSecondary: '#FFFFFF',
    secondaryContainer: '#DCE8D6',
    onSecondaryContainer: '#16250F',
    tertiary: '#6FA33A',
    onTertiary: '#FFFFFF',
    tertiaryContainer: '#DCF0CB',
    onTertiaryContainer: '#1B2E06',
    error: '#A1514A',
    onError: '#FFFFFF',
    errorContainer: '#F5DAD7',
    onErrorContainer: '#3F1512',
    /** Semantic amber for "medium priority" / attention. */
    warning: '#7E5F2A',
    onWarning: '#FFFFFF',
    warningContainer: '#F0E2C6',
    onWarningContainer: '#3A2A0C',
    background: '#F5F7F4',
    onBackground: '#1A2118',
    surface: '#F5F7F4',
    onSurface: '#1A2118',
    surfaceVariant: '#DFE7DB',
    onSurfaceVariant: '#586152',
    surfaceContainerLowest: '#FFFFFF',
    surfaceContainerLow: '#EEF2EC',
    surfaceContainer: '#E7EDE4',
    surfaceContainerHigh: '#DFE7DB',
    surfaceContainerHighest: '#D8E1D3',
    outline: '#7C877A',
    outlineVariant: '#C6CFC2',
    scrim: 'rgba(12,20,10,0.45)',
    inverseSurface: '#2E362B',
    inverseOnSurface: '#EFF2EC',
    inversePrimary: '#A9D89A',
    shadow: '#1A2820',
    focusRing: '#417A34',

    // ---- semantic aliases (component-facing names) ----
    /** Raised card / page surface. */
    paper: '#F5F7F4',
    /** Recessed / grouped surface. */
    panel: '#EEF2EC',
    /** Hairline divider. */
    line: '#C6CFC2',
    /** Stronger border for outlined controls. */
    lineStrong: '#7C877A',
    /** Primary text. */
    ink: '#1A2118',
    /** Secondary text. */
    inkMuted: '#586152',
    /** Placeholder / disabled text. */
    inkFaint: '#7C877A',
    /** Text on a filled ink/primary surface. */
    onInk: '#FFFFFF',
    /** The live "now" colour. */
    now: '#6FA33A',
    nowContainer: '#DCF0CB',
    onNow: '#1B2E06',
    /** State layers. */
    hover: 'rgba(26,33,24,0.06)',
    pressed: 'rgba(26,33,24,0.12)',
  },
  dark: {
    primary: '#A9D89A',
    onPrimary: '#12330B',
    primaryContainer: '#2C5222',
    onPrimaryContainer: '#CBECC0',
    secondary: '#B6CDB0',
    onSecondary: '#213520',
    secondaryContainer: '#374B34',
    onSecondaryContainer: '#DCE8D6',
    tertiary: '#A5D07A',
    onTertiary: '#22330A',
    tertiaryContainer: '#3A5220',
    onTertiaryContainer: '#DCF0CB',
    error: '#E8A9A2',
    onError: '#4A100C',
    errorContainer: '#6E2A24',
    onErrorContainer: '#F5DAD7',
    warning: '#E0BD84',
    onWarning: '#3A2A0C',
    warningContainer: '#4A3A1C',
    onWarningContainer: '#F0E2C6',
    background: '#11150F',
    onBackground: '#E4E9E0',
    surface: '#11150F',
    onSurface: '#E4E9E0',
    surfaceVariant: '#3F463A',
    onSurfaceVariant: '#BFC7B8',
    surfaceContainerLowest: '#0C1009',
    surfaceContainerLow: '#191E16',
    surfaceContainer: '#1D231A',
    surfaceContainerHigh: '#272E23',
    surfaceContainerHighest: '#32392D',
    outline: '#8A9384',
    outlineVariant: '#3F463A',
    scrim: 'rgba(0,0,0,0.6)',
    inverseSurface: '#E4E9E0',
    inverseOnSurface: '#2E362B',
    inversePrimary: '#417A34',
    shadow: '#000000',
    focusRing: '#A9D89A',
    paper: '#11150F',
    panel: '#191E16',
    line: '#3F463A',
    lineStrong: '#8A9384',
    ink: '#E4E9E0',
    inkMuted: '#BFC7B8',
    inkFaint: '#8A9384',
    onInk: '#11150F',
    now: '#A5D07A',
    nowContainer: '#3A5220',
    onNow: '#DCF0CB',
    hover: 'rgba(228,233,224,0.06)',
    pressed: 'rgba(228,233,224,0.12)',
  },
} as const;

export type ThemeName = keyof typeof Palette;
export type ThemeColorKey = keyof (typeof Palette)['light'];
export type ThemeColors = Record<ThemeColorKey, string>;

/** Material 3 elevation. Soft, green-tinted shadows + a top highlight. */
export const Elevation = {
  level0: 'none',
  level1: '0 1px 2px rgba(26,40,24,0.08), 0 1px 3px rgba(26,40,24,0.06)',
  level2: '0 2px 4px rgba(26,40,24,0.09), 0 4px 8px rgba(26,40,24,0.07)',
  level3: '0 4px 8px rgba(26,40,24,0.09), 0 8px 20px rgba(26,40,24,0.09)',
  level4: '0 6px 12px rgba(26,40,24,0.1), 0 12px 28px rgba(26,40,24,0.11)',
  level5: '0 8px 16px rgba(26,40,24,0.12), 0 16px 36px rgba(26,40,24,0.13)',
  /** Add to a raised surface for the micro-skeuomorphic edge light. */
  highlight: 'inset 0 1px 0 rgba(255,255,255,0.7)',
  /** Pressed state. */
  inset: 'inset 0 1px 2px rgba(26,40,24,0.12)',
} as const;

export type ElevationLevel = keyof Omit<typeof Elevation, 'highlight' | 'inset'>;

export const Space = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

/** Material 3 shape scale. */
export const Radius = {
  none: 0,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 28,
  pill: 999,
} as const;

/** Material 3 type scale. Legacy aliases kept so existing rhythm does not shift. */
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
  // MD3
  displaySmall: 36,
  headlineSmall: 24,
  titleLarge: 22,
  titleMedium: 16,
  titleSmall: 14,
  bodyLarge: 16,
  bodyMedium: 14,
  bodySmall: 12,
  labelLarge: 14,
  labelMedium: 12,
  labelSmall: 11,
} as const;

/** Material 3 line heights, paired with the type scale above. */
export const LineHeight = {
  displaySmall: 44,
  headlineSmall: 32,
  titleLarge: 28,
  titleMedium: 24,
  titleSmall: 20,
  bodyLarge: 26,
  bodyMedium: 22,
  bodySmall: 18,
  labelLarge: 20,
  labelMedium: 16,
  labelSmall: 16,
} as const;

export const Line = {
  tight: 1.3,
  normal: 1.5,
  relaxed: 1.6,
} as const;

/** State layer opacity (MD3). */
export const StateLayer = {
  hover: 0.06,
  focus: 0.12,
  pressed: 0.12,
  drag: 0.16,
} as const;

export const Fonts = {
  mono: 'IBMPlexMono_500Medium',
  monoRegular: 'IBMPlexMono_400Regular',
  sans: Platform.OS === 'web' ? 'var(--font-sans)' : undefined,
} as const;

export const Layout = {
  /** Material 3 "medium" breakpoint: below it, bottom bar + single column. */
  breakpoint: 840,
  railWidth: 88,
  navBarHeight: 80,
  contentMax: 880,
  padWide: 32,
  padNarrow: 16,
  headerHeight: 64,
} as const;

export const Motion = {
  entrance: 240,
  standard: 200,
  emphasized: 400,
} as const;
