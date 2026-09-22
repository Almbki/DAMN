import Svg, { Circle, Path } from 'react-native-svg';

/**
 * Hand-drawn line icons — stroke only, no fill, round caps and joins — so the
 * navigation reads the same on every platform. There is deliberately no icon
 * font and no third-party icon set; four glyphs is all the app needs.
 *
 * Colour is always passed in by the caller (`ink` / `inkMuted` / `accent`), never
 * baked here: the same rule as everywhere else, components do not own colours.
 */

export type IconProps = {
  /** Roughly 20–22 at the default text scale. */
  size?: number;
  color: string;
};

const STROKE = 1.75;

/** TODO — a two-line checklist. */
export function TodoIcon({ size = 22, color }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path
        d="M3.5 6.6 5.9 9 10.3 4.6"
        stroke={color}
        strokeWidth={STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path d="M13.6 7h6.9" stroke={color} strokeWidth={STROKE} strokeLinecap="round" />
      <Path
        d="M3.5 17.1 5.9 19.5 10.3 15.1"
        stroke={color}
        strokeWidth={STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path d="M13.6 17.5h6.9" stroke={color} strokeWidth={STROKE} strokeLinecap="round" />
    </Svg>
  );
}

/** 画像 — a head over shoulders. */
export function ProfileIcon({ size = 22, color }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Circle cx={12} cy={8} r={3.6} stroke={color} strokeWidth={STROKE} />
      <Path
        d="M5 20c0-3.9 3.1-6.4 7-6.4s7 2.5 7 6.4"
        stroke={color}
        strokeWidth={STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Svg>
  );
}

/** GOAL — a target. */
export function GoalIcon({ size = 22, color }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Circle cx={12} cy={12} r={8} stroke={color} strokeWidth={STROKE} />
      <Circle cx={12} cy={12} r={3.6} stroke={color} strokeWidth={STROKE} />
      <Circle cx={12} cy={12} r={1} stroke={color} strokeWidth={STROKE} />
    </Svg>
  );
}

/** 设置 — two sliders. */
export function SettingsIcon({ size = 22, color }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d="M4 8h6.2" stroke={color} strokeWidth={STROKE} strokeLinecap="round" />
      <Circle cx={13.5} cy={8} r={2.6} stroke={color} strokeWidth={STROKE} />
      <Path d="M16.1 8H20" stroke={color} strokeWidth={STROKE} strokeLinecap="round" />
      <Path d="M4 16h9.2" stroke={color} strokeWidth={STROKE} strokeLinecap="round" />
      <Circle cx={16.5} cy={16} r={2.6} stroke={color} strokeWidth={STROKE} />
      <Path d="M19.1 16H20" stroke={color} strokeWidth={STROKE} strokeLinecap="round" />
    </Svg>
  );
}

/** Keyed lookup for `NAV`; keeps the shell from holding a switch. */
export const NAV_ICONS = {
  todo: TodoIcon,
  profile: ProfileIcon,
  goal: GoalIcon,
  settings: SettingsIcon,
} as const;
