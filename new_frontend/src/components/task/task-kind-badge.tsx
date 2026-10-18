import { StyleSheet, Text, View } from 'react-native';

import { Radius, Space, Type } from '@/constants/tokens';
import { formatShort } from '@/domain/date';
import { TASK_KIND_LABEL, type TaskKind } from '@/domain/task';
import { useTheme } from '@/state/theme';

/**
 * A quiet marker for work that repeats over time. `one_off` stays implicit:
 * most tasks are one-off, and a badge on every row would just add noise.
 *
 * Long-term series also carry their progress (`第 N 天`) or the occurrence date;
 * routines stay a single word so the row never wraps into a second line.
 */
export function TaskKindBadge({
  taskKind,
  seriesIndex = null,
  occurrenceDate = null,
}: {
  taskKind: TaskKind;
  seriesIndex?: number | null;
  occurrenceDate?: string | null;
}) {
  const { colors } = useTheme();
  if (taskKind === 'one_off') return null;

  const palette =
    taskKind === 'routine'
      ? { background: colors.tertiaryContainer, foreground: colors.onTertiaryContainer }
      : { background: colors.secondaryContainer, foreground: colors.onSecondaryContainer };

  const series =
    taskKind === 'long_term'
      ? seriesIndex != null
        ? `第 ${seriesIndex + 1} 天`
        : occurrenceDate
          ? formatShort(occurrenceDate)
          : null
      : null;

  return (
    <View style={styles.wrap}>
      <View style={[styles.badge, { backgroundColor: palette.background }]}>
        <Text style={[styles.text, { color: palette.foreground }]}>
          {TASK_KIND_LABEL[taskKind]}
        </Text>
      </View>
      {series ? <Text style={[styles.series, { color: colors.inkMuted }]}>{series}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
  },
  badge: {
    borderRadius: Radius.pill,
    paddingHorizontal: Space.sm,
    paddingVertical: 1,
  },
  text: {
    fontSize: Type.labelSmall,
    fontWeight: '600',
    lineHeight: Type.labelSmall * 1.4,
  },
  series: {
    fontSize: Type.labelSmall,
  },
});
