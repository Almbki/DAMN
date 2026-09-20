import { StyleSheet, Text, View } from 'react-native';

import { Radius, Space, Type } from '@/constants/tokens';
import type { Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

const SEGMENTS = 48;
const SIZE = 220;
const RADIUS = 82;
const TICK_W = 3;
const TICK_H = 16;

/**
 * Circular progress chart: one tick per segment around a ring.
 *
 * Built from plain views (rotate + translate) so there is no charting or SVG
 * dependency. Completed ticks are ink, skipped are faint, the rest are the
 * hairline colour — the same "paper and line" language as the rest of the app.
 */
export function CircularChart({ tasks }: { tasks: Task[] }) {
  const { colors } = useTheme();
  const total = tasks.length;
  const done = tasks.filter((task) => task.done).length;
  const skipped = tasks.filter((task) => task.skipped).length;
  const open = total - done - skipped;
  const ratio = total === 0 ? 0 : done / total;
  const doneTicks = Math.round(ratio * SEGMENTS);
  const skippedTicks = total === 0 ? 0 : Math.round((skipped / total) * SEGMENTS);

  return (
    <View style={styles.wrap}>
      <View
        accessibilityRole="image"
        accessibilityLabel={`已完成 ${done} 项，共 ${total} 项`}
        style={styles.ring}>
        {Array.from({ length: SEGMENTS }).map((_, index) => {
          const angle = (index / SEGMENTS) * 360;
          const color =
            index < doneTicks
              ? colors.ink
              : index < doneTicks + skippedTicks
                ? colors.inkFaint
                : colors.line;
          return (
            <View
              key={index}
              style={[
                styles.tick,
                { backgroundColor: color, transform: [{ rotate: `${angle}deg` }, { translateY: -RADIUS }] },
              ]}
            />
          );
        })}

        <View style={styles.center}>
          <View style={styles.centerRow}>
            <Text style={[styles.big, { color: colors.ink }]}>{done}</Text>
            <Text style={[styles.total, { color: colors.inkMuted }]}>/{total}</Text>
          </View>
          <Text style={[styles.caption, { color: colors.inkMuted }]}>
            {total === 0 ? '暂无任务' : `已完成 ${Math.round(ratio * 100)}%`}
          </Text>
        </View>
      </View>

      <View style={styles.legend}>
        <Legend label="已完成" value={done} color={colors.ink} />
        <Legend label="已跳过" value={skipped} color={colors.inkFaint} />
        <Legend label="未完成" value={open} color={colors.line} />
      </View>
    </View>
  );
}

function Legend({ label, value, color }: { label: string; value: number; color: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.legendItem}>
      <View style={[styles.legendDot, { backgroundColor: color }]} />
      <Text style={[styles.legendText, { color: colors.inkMuted }]}>
        {label} <Text style={styles.legendValue}>{value}</Text>
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    gap: Space.lg,
    paddingVertical: Space.lg,
  },
  ring: {
    width: SIZE,
    height: SIZE,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tick: {
    position: 'absolute',
    top: SIZE / 2 - TICK_H / 2,
    left: SIZE / 2 - TICK_W / 2,
    width: TICK_W,
    height: TICK_H,
    borderRadius: Radius.sm / 2,
  },
  center: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Space.xs,
    pointerEvents: 'none',
  },
  centerRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: Space.xs,
  },
  big: {
    fontSize: 56,
    lineHeight: 60,
    fontFamily: 'IBMPlexMono_500Medium',
  },
  total: {
    fontSize: Type.title,
    fontFamily: 'IBMPlexMono_400Regular',
  },
  caption: {
    fontSize: Type.small,
  },
  legend: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.lg,
    justifyContent: 'center',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 2,
  },
  legendText: {
    fontSize: Type.small,
  },
  legendValue: {
    fontFamily: 'IBMPlexMono_500Medium',
  },
});
