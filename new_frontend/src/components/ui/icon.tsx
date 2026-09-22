import { StyleSheet, View, type ViewStyle } from 'react-native';

import { useTheme } from '@/state/theme';

/**
 * Geometry-only icon set. No icon font / SVG dependency, so it renders the
 * same on web and native and never flashes a missing glyph. Every icon is drawn
 * inside a square of `size`, positioned in percentages.
 */

export type IconName =
  | 'check'
  | 'close'
  | 'plus'
  | 'minus'
  | 'chevronDown'
  | 'chevronRight'
  | 'list'
  | 'chart'
  | 'target'
  | 'sliders'
  | 'swap'
  | 'arrowRight'
  | 'calendar'
  | 'clock'
  | 'dot'
  | 'menu'
  | 'flag';

export function Icon({
  name,
  size = 20,
  color,
  strokeWidth = 2,
}: {
  name: IconName;
  size?: number;
  color?: string;
  strokeWidth?: number;
}) {
  const { colors } = useTheme();
  const c = color ?? colors.ink;
  const s = strokeWidth;

  return <View style={{ width: size, height: size }}>{renderIcon(name, size, c, s)}</View>;
}

function bar(style: ViewStyle) {
  return <View style={[styles.bar, style]} />;
}

function triangle(style: ViewStyle) {
  return <View style={[styles.bar, style]} />;
}

function renderIcon(name: IconName, size: number, color: string, s: number) {
  const half = size / 2;

  switch (name) {
    case 'check':
      return (
        <>
          {bar({
            width: size * 0.34,
            height: s,
            borderRadius: s,
            left: size * 0.12,
            top: size * 0.6,
            backgroundColor: color,
            transform: [{ rotate: '45deg' }],
          })}
          {bar({
            width: size * 0.6,
            height: s,
            borderRadius: s,
            left: size * 0.32,
            top: size * 0.44,
            backgroundColor: color,
            transform: [{ rotate: '-45deg' }],
          })}
        </>
      );

    case 'close':
      return (
        <>
          {bar({
            width: size * 0.7,
            height: s,
            borderRadius: s,
            left: size * 0.15,
            top: half - s / 2,
            backgroundColor: color,
            transform: [{ rotate: '45deg' }],
          })}
          {bar({
            width: size * 0.7,
            height: s,
            borderRadius: s,
            left: size * 0.15,
            top: half - s / 2,
            backgroundColor: color,
            transform: [{ rotate: '-45deg' }],
          })}
        </>
      );

    case 'plus':
      return (
        <>
          {bar({
            width: size * 0.68,
            height: s,
            borderRadius: s,
            left: size * 0.16,
            top: half - s / 2,
            backgroundColor: color,
          })}
          {bar({
            width: s,
            height: size * 0.68,
            borderRadius: s,
            left: half - s / 2,
            top: size * 0.16,
            backgroundColor: color,
          })}
        </>
      );

    case 'minus':
      return bar({
        width: size * 0.68,
        height: s,
        borderRadius: s,
        left: size * 0.16,
        top: half - s / 2,
        backgroundColor: color,
      });

    case 'chevronDown':
      return (
        <>
          {bar({
            width: size * 0.42,
            height: s,
            borderRadius: s,
            left: size * 0.16,
            top: size * 0.42,
            backgroundColor: color,
            transform: [{ rotate: '45deg' }],
          })}
          {bar({
            width: size * 0.42,
            height: s,
            borderRadius: s,
            left: size * 0.42,
            top: size * 0.42,
            backgroundColor: color,
            transform: [{ rotate: '-45deg' }],
          })}
        </>
      );

    case 'chevronRight':
      return (
        <>
          {bar({
            width: size * 0.42,
            height: s,
            borderRadius: s,
            left: size * 0.28,
            top: size * 0.3,
            backgroundColor: color,
            transform: [{ rotate: '45deg' }],
          })}
          {bar({
            width: size * 0.42,
            height: s,
            borderRadius: s,
            left: size * 0.28,
            top: size * 0.5,
            backgroundColor: color,
            transform: [{ rotate: '-45deg' }],
          })}
        </>
      );

    case 'arrowRight':
      return (
        <>
          {bar({
            width: size * 0.56,
            height: s,
            borderRadius: s,
            left: size * 0.14,
            top: half - s / 2,
            backgroundColor: color,
          })}
          {triangle({
            width: 0,
            height: 0,
            left: size * 0.62,
            top: half - size * 0.15,
            borderTopWidth: size * 0.15,
            borderBottomWidth: size * 0.15,
            borderLeftWidth: size * 0.18,
            borderTopColor: 'transparent',
            borderBottomColor: 'transparent',
            borderLeftColor: color,
          })}
        </>
      );

    case 'list':
    case 'menu':
      return (
        <>
          {bar({ width: size * 0.78, height: s, borderRadius: s, left: size * 0.11, top: size * 0.26, backgroundColor: color })}
          {bar({ width: size * 0.78, height: s, borderRadius: s, left: size * 0.11, top: half - s / 2, backgroundColor: color })}
          {bar({ width: size * 0.52, height: s, borderRadius: s, left: size * 0.11, top: size * 0.74 - s, backgroundColor: color })}
        </>
      );

    case 'chart':
      return (
        <>
          {bar({ width: size * 0.16, height: size * 0.34, borderRadius: s / 2, left: size * 0.14, top: size * 0.56, backgroundColor: color })}
          {bar({ width: size * 0.16, height: size * 0.56, borderRadius: s / 2, left: size * 0.42, top: size * 0.34, backgroundColor: color })}
          {bar({ width: size * 0.16, height: size * 0.44, borderRadius: s / 2, left: size * 0.7, top: size * 0.46, backgroundColor: color })}
        </>
      );

    case 'target':
      return (
        <>
          {bar({
            width: size * 0.72,
            height: size * 0.72,
            borderRadius: size,
            left: size * 0.14,
            top: size * 0.14,
            borderWidth: s,
            borderColor: color,
          })}
          {bar({
            width: size * 0.2,
            height: size * 0.2,
            borderRadius: size,
            left: size * 0.4,
            top: size * 0.4,
            backgroundColor: color,
          })}
        </>
      );

    case 'sliders':
      return (
        <>
          {bar({ width: size * 0.78, height: s, borderRadius: s, left: size * 0.11, top: size * 0.28, backgroundColor: color })}
          {bar({ width: size * 0.78, height: s, borderRadius: s, left: size * 0.11, top: half - s / 2, backgroundColor: color })}
          {bar({ width: size * 0.78, height: s, borderRadius: s, left: size * 0.11, top: size * 0.72 - s, backgroundColor: color })}
          {bar({ width: size * 0.2, height: size * 0.2, borderRadius: size, left: size * 0.18, top: size * 0.18, backgroundColor: color })}
          {bar({ width: size * 0.2, height: size * 0.2, borderRadius: size, left: size * 0.56, top: size * 0.4, backgroundColor: color })}
          {bar({ width: size * 0.2, height: size * 0.2, borderRadius: size, left: size * 0.34, top: size * 0.62, backgroundColor: color })}
        </>
      );

    case 'swap':
      return (
        <>
          {bar({ width: size * 0.5, height: s, borderRadius: s, left: size * 0.16, top: size * 0.34, backgroundColor: color })}
          {triangle({
            width: 0,
            height: 0,
            left: size * 0.62,
            top: size * 0.24,
            borderTopWidth: size * 0.1,
            borderBottomWidth: size * 0.1,
            borderLeftWidth: size * 0.14,
            borderTopColor: 'transparent',
            borderBottomColor: 'transparent',
            borderLeftColor: color,
          })}
          {bar({ width: size * 0.5, height: s, borderRadius: s, left: size * 0.34, top: size * 0.62, backgroundColor: color })}
          {triangle({
            width: 0,
            height: 0,
            left: size * 0.24,
            top: size * 0.52,
            borderTopWidth: size * 0.1,
            borderBottomWidth: size * 0.1,
            borderRightWidth: size * 0.14,
            borderTopColor: 'transparent',
            borderBottomColor: 'transparent',
            borderRightColor: color,
          })}
        </>
      );

    case 'calendar':
      return (
        <>
          {bar({
            width: size * 0.76,
            height: size * 0.68,
            borderRadius: size * 0.14,
            left: size * 0.12,
            top: size * 0.2,
            borderWidth: s,
            borderColor: color,
          })}
          {bar({ width: size * 0.76, height: s, left: size * 0.12, top: size * 0.4, backgroundColor: color })}
          {bar({ width: s, height: size * 0.16, borderRadius: s, left: size * 0.28, top: size * 0.1, backgroundColor: color })}
          {bar({ width: s, height: size * 0.16, borderRadius: s, left: size * 0.66, top: size * 0.1, backgroundColor: color })}
        </>
      );

    case 'clock':
      return (
        <>
          {bar({
            width: size * 0.76,
            height: size * 0.76,
            borderRadius: size,
            left: size * 0.12,
            top: size * 0.12,
            borderWidth: s,
            borderColor: color,
          })}
          {bar({ width: s, height: size * 0.24, borderRadius: s, left: half - s / 2, top: size * 0.26, backgroundColor: color })}
          {bar({ width: size * 0.2, height: s, borderRadius: s, left: half, top: size * 0.48, backgroundColor: color })}
        </>
      );

    case 'dot':
      return bar({
        width: size * 0.5,
        height: size * 0.5,
        borderRadius: size,
        left: size * 0.25,
        top: size * 0.25,
        backgroundColor: color,
      });

    case 'flag':
      return (
        <>
          {bar({
            width: Math.max(1.5, s * 0.8),
            height: size * 0.72,
            borderRadius: s,
            left: size * 0.26,
            top: size * 0.16,
            backgroundColor: color,
          })}
          {triangle({
            width: 0,
            height: 0,
            left: size * 0.3,
            top: size * 0.2,
            borderTopWidth: size * 0.14,
            borderBottomWidth: size * 0.14,
            borderLeftWidth: size * 0.42,
            borderTopColor: 'transparent',
            borderBottomColor: 'transparent',
            borderLeftColor: color,
          })}
        </>
      );

    default:
      return null;
  }
}

const styles = StyleSheet.create({
  bar: {
    position: 'absolute',
  },
});
