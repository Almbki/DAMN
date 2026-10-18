import { StyleSheet, Text, View } from 'react-native';

import { TaskKindBadge } from '@/components/task/task-kind-badge';
import { Space, Type } from '@/constants/tokens';
import { formatShort, todayISO } from '@/domain/date';
import { isClosed, repeatLabel, type Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

/** Meta line: kind badge, due date/time and repeat rule. */
export function TaskMeta({ task }: { task: Task }) {
  const { colors } = useTheme();
  const overdue = task.dueDate && task.dueDate < todayISO() && !isClosed(task);
  const repeat = repeatLabel(task.repeat);
  const hasKind = task.taskKind !== 'one_off';

  if (!task.dueDate && !repeat && !task.startTime && !hasKind) return null;

  return (
    <View style={styles.meta}>
      <TaskKindBadge
        taskKind={task.taskKind}
        seriesIndex={task.seriesIndex}
        occurrenceDate={task.occurrenceDate}
      />

      {task.dueDate ? (
        <Text
          style={[
            styles.metaText,
            { color: overdue ? colors.ink : colors.inkMuted, fontWeight: overdue ? '700' : '400' },
          ]}>
          {formatShort(task.dueDate)}
          {task.dueTime ? ` ${task.dueTime}` : ''}
        </Text>
      ) : null}

      {repeat ? <Text style={[styles.metaText, { color: colors.inkMuted }]}>↻ {repeat}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    flexWrap: 'wrap',
  },
  metaText: {
    fontSize: Type.small,
  },
});
