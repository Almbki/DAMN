import { StyleSheet, Text, View } from 'react-native';

import { Radius, Space, Type } from '@/constants/tokens';
import { addDays, diffDays, parseISO, todayISO } from '@/domain/date';
import { isClosed, type Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

/**
 * Lightweight Gantt-style timeline. Bars are laid out with percentages so no
 * measurement is required at any width; the mint marker is the same "now" signal
 * used by the ruler.
 */
export function Timeline({ tasks, days = 14 }: { tasks: Task[]; days?: number }) {
  const { colors } = useTheme();
  const today = todayISO();
  const start = addDays(today, -1);

  const dated = tasks.filter((task) => task.dueDate);
  const todayOffset = diffDays(start, today);
  const todayPercent = (todayOffset / days) * 100;

  const labels: string[] = [];
  for (let offset = 0; offset < days; offset += 3) {
    const date = addDays(start, offset);
    const parsed = parseISO(date);
    labels.push(`${parsed.getMonth() + 1}/${parsed.getDate()}`);
  }

  return (
    <View style={styles.wrap}>
      <View style={styles.header}>
        <View style={styles.headerSpacer} />
        <View style={styles.headerTrack}>
          {labels.map((label, index) => (
            <Text
              key={label}
              style={[styles.headerLabel, { color: colors.inkMuted, left: `${((index * 3) / days) * 100}%` }]}>
              {label}
            </Text>
          ))}
        </View>
      </View>

      {dated.length === 0 ? (
        <Text style={[styles.empty, { color: colors.inkMuted }]}>
          有时间线的任务会出现在这里。给任务加上日期试试。
        </Text>
      ) : (
        dated.map((task) => {
          const barStart = task.startDate ?? task.dueDate ?? today;
          const span = task.startDate && task.dueDate ? Math.max(1, diffDays(task.startDate, task.dueDate) + 1) : 1;
          const offset = diffDays(start, barStart);
          const left = Math.max(0, Math.min(100, (offset / days) * 100));
          const width = Math.max(3, Math.min(100 - left, (span / days) * 100));
          const containsToday = offset <= todayOffset && offset + span - 1 >= todayOffset;
          const color = isClosed(task) ? colors.inkFaint : containsToday ? colors.mint : colors.ink;

          return (
            <View key={task.id} style={styles.row}>
              <Text style={[styles.rowLabel, { color: colors.ink }]} numberOfLines={1}>
                {task.title}
              </Text>
              <View style={[styles.track, { backgroundColor: colors.panel, borderColor: colors.line }]}>
                <View style={[styles.today, { backgroundColor: colors.line, left: `${todayPercent}%` }]} />
                <View style={[styles.bar, { backgroundColor: color, left: `${left}%`, width: `${width}%` }]} />
              </View>
            </View>
          );
        })
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: Space.sm,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
  },
  headerSpacer: {
    width: 120,
  },
  headerTrack: {
    flex: 1,
    height: 16,
  },
  headerLabel: {
    position: 'absolute',
    fontSize: Type.micro,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    minHeight: 32,
  },
  rowLabel: {
    width: 120,
    fontSize: Type.small,
  },
  track: {
    flex: 1,
    height: 18,
    borderRadius: Radius.sm,
    borderWidth: 1,
    overflow: 'hidden',
  },
  today: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 1,
  },
  bar: {
    position: 'absolute',
    top: 3,
    bottom: 3,
    borderRadius: Radius.sm,
  },
  empty: {
    fontSize: Type.small,
  },
});
