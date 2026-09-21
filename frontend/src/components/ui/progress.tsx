import { StyleSheet, View } from 'react-native';

import { useTheme } from '@/state/theme';

/** Material 3 linear progress. `value` is clamped to 0..1. */
export function Progress({
  value,
  color,
  trackColor,
  height = 8,
}: {
  value: number;
  color?: string;
  trackColor?: string;
  height?: number;
}) {
  const { colors } = useTheme();
  const ratio = Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : 0;
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: Math.round(ratio * 100) }}
      style={[
        styles.track,
        { height, borderRadius: height / 2, backgroundColor: trackColor ?? colors.surfaceContainerHighest },
      ]}>
      <View
        style={[
          styles.fill,
          { width: `${ratio * 100}%`, borderRadius: height / 2, backgroundColor: color ?? colors.primary },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    width: '100%',
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
  },
});
