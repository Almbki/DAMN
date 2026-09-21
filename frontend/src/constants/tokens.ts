import '@/global.css';

import { Platform } from 'react-native';

/**
 * DAMN design tokens — 「雾桉」(frosted eucalyptus).
 *
 * A low-saturation cool grey-green. The accent means "now" and nothing else:
 * the current item, the primary button, progress. Completion never borrows a
 * second colour — it fades to ink and strikes through.
 *
 * Height is the whole elevation system: four levels, one shadow implementation
 * (`components/surface.tsx`). Components never write a shadow or a colour
 * literal themselves.
 */

export const Palette = {
  light: {
    paper: '#F5F6F3',
    panel: '#EDEFEA',
    raised: '#FFFFFF',
    line: '#E2E5E0',
    ink: '#252924',
    inkMuted: '#5F665F',
    inkFaint: '#9AA098',
    accent: '#4F7A66',
    accentSoft: '#E0EAE4',
    onAccent: '#FFFFFF',
    hover: 'rgba(37,41,36,0.05)',
    pressed: 'rgba(37,41,36,0.09)',
    /** MD ripple on paper/panel surfaces (animated to 18% then out). */
    ripple: '#252924',
    /** MD ripple on an accent-filled surface. */
    rippleOnAccent: '#FFFFFF',
    /** The bottom bar's active pill: a light stadium on the panel. */
    navPill: '#FFFFFF',
  },
  dark: {
    paper: '#151816',
    panel: '#1C201D',
    raised: '#1C201D',
    line: '#2A2F2B',
    ink: '#E6E9E4',
    inkMuted: '#9BA39B',
    inkFaint: '#6A7269',
    accent: '#96BFA9',
    accentSoft: '#223129',
    onAccent: '#101512',
    hover: 'rgba(230,233,228,0.06)',
    pressed: 'rgba(230,233,228,0.10)',
    ripple: '#E6E9E4',
    rippleOnAccent: '#101512',
    navPill: '#333833',
  },
} as const;

export type ThemeName = keyof typeof Palette;
export type ThemeColorKey = keyof (typeof Palette)['light'];
export type ThemeColors = Record<ThemeColorKey, string>;

/**
 * Four levels of height. `flat` divides with a hairline and stays for list rows,
 * blocks and charts; `raised` means a component sits above the page (cards,
 * buttons); `overlay` floats; `inset` has already happened (pressed / selected /
 * done). "Raised" is about height above the page, not merely clickability.
 */
export type Elevation = 'flat' | 'raised' | 'overlay' | 'inset';

export type SurfaceStyle = {
  boxShadow: string;
  /** Dark mode has no outer shadow: a white layer lifts the surface instead. */
  overlayColor?: string;
  /** Dark `raised` replaces the shadow with a 1px top highlight. */
  highlightColor?: string;
};

export const ElevationTokens: Record<ThemeName, Record<Elevation, SurfaceStyle>> = {
  light: {
    flat: { boxShadow: 'none' },
    raised: {
      boxShadow: '0 1px 2px rgba(30,34,31,0.09), 0 6px 18px rgba(30,34,31,0.13)',
    },
    overlay: { boxShadow: '0 12px 36px rgba(30,34,31,0.22), 0 2px 8px rgba(30,34,31,0.10)' },
    inset: {
      boxShadow:
        'inset 0 2px 4px rgba(30,34,31,0.18), inset 0 -1px 0 rgba(255,255,255,0.70)',
    },
  },
  dark: {
    flat: { boxShadow: 'none' },
    raised: {
      boxShadow: 'none',
      overlayColor: 'rgba(230,233,228,0.07)',
      highlightColor: 'rgba(230,233,228,0.14)',
    },
    overlay: { boxShadow: 'none', overlayColor: 'rgba(230,233,228,0.11)' },
    inset: {
      boxShadow:
        'inset 0 2px 5px rgba(0,0,0,0.62), inset 0 1px 0 rgba(255,255,255,0.05)',
    },
  },
};

export const Space = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

/** Radii follow the level: the more it floats, the rounder it is. */
export const Radius = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  full: 999,
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

/** MD3 motion. Motion only ever answers an action. */
export const Duration = {
  short: 150,
  /** Upper end of MD3's "short"; used where 150ms reads as a snap. */
  shortLong: 200,
  medium: 300,
  long: 500,
} as const;

export const Easing = {
  standard: 'cubic-bezier(0.2,0,0,1)',
  decelerate: 'cubic-bezier(0.05,0.7,0.1,1)',
  accelerate: 'cubic-bezier(0.3,0,0.8,0.15)',
} as const;

/**
 * The keyboard focus ring. Thinner than the 2px in the first draft — the user
 * found a 2px box too heavy. It only appears for keyboard navigation; see
 * `hooks/use-input-modality.ts`.
 */
export const RingWidth = 1.5;

/**
 * RN's `Animated` needs the JS driver on web and the native driver elsewhere.
 * Kept here so components never reach for `Platform` themselves.
 */
export const Motion = {
  nativeDriver: Platform.OS !== 'web',
} as const;

/**
 * Material press ripple. A circle grows from the touch point and fades out; it
 * only ever answers a press, never decoration.
 */
export const Ripple = {
  /** Long enough to read as a glow, short enough not to delay the action. */
  duration: 350,
  /** Final scale of a circle sized to the surface diagonal. */
  scale: 2.2,
  /** Peak opacity, then it fades to zero. */
  opacity: 0.18,
} as const;

/** Press is the only scale the design uses. */
export const PressScale = 0.98;
