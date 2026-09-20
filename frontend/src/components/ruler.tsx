import { useEffect, useState } from 'react';
import { Animated, Easing, StyleSheet, View } from 'react-native';

import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { Motion } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

export type RulerState = 'done' | 'now' | 'todo';

export type RulerSegment = { key: string; state: RulerState };

/**
 * The signature element: one tick per task in the day.
 *
 * Mint means "now" and appears here and nowhere else in the layout. On mount the
 * live tick grows once — the page's single orchestrated motion. Everything else
 * is still.
 */
export function Ruler({ segments }: { segments: RulerSegment[] }) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const [progress] = useState(() => new Animated.Value(0));

  useEffect(() => {
    if (reduced) {
      progress.setValue(1);
      return;
    }
    const animation = Animated.timing(progress, {
      toValue: 1,
      duration: Motion.entrance,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: false,
    });
    animation.start();
    return () => animation.stop();
  }, [progress, reduced]);

  return (
    <View style={styles.wrap}>
      <View style={[styles.ticks, { borderBottomColor: colors.line }]}>
        {segments.map((segment) => {
          const isNow = segment.state === 'now';
          const color =
            segment.state === 'done' ? colors.ink : isNow ? colors.mint : colors.line;
          const height = isNow ? 34 : segment.state === 'done' ? 18 : 12;
          const width = isNow ? 3 : 2;

          if (!isNow) {
            return (
              <View
                key={segment.key}
                style={{ width, height, borderRadius: 1, backgroundColor: color }}
              />
            );
          }

          return (
            <Animated.View
              key={segment.key}
              style={{
                width,
                borderRadius: 1,
                backgroundColor: colors.mint,
                height: progress.interpolate({ inputRange: [0, 1], outputRange: [8, height] }),
                opacity: progress,
              }}
            />
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: 6,
  },
  ticks: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 6,
    paddingBottom: 6,
    borderBottomWidth: 1,
    minHeight: 40,
  },
});
