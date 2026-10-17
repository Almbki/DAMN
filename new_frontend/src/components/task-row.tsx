import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DotsButton } from '@/components/task/dots-button';
import { TaskMeta } from '@/components/task-meta';
import { Checkbox } from '@/components/ui/checkbox';
import { useInteraction } from '@/components/ui/interaction';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { isClosed, type Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

type Props = {
  task: Task;
  /** Keyboard/roving highlight. */
  active?: boolean;
  onToggleDone: () => void;
  /** Opens the task detail sheet. */
  onOpen?: () => void;
};

/**
 * A Material 3 list row. The row is a plain container; the checkbox, the
 * content button and the overflow button are siblings (nesting pressables emits
 * invalid HTML on react-native-web).
 */
export function TaskRow({ task, active = false, onToggleDone, onOpen }: Props) {
  const { colors } = useTheme();
  const { focused, onFocus, onBlur } = useInteraction();
  const done = task.done;
  const skipped = task.skipped;

  return (
    <View
      style={[
        styles.row,
        {
          borderBottomColor: colors.outlineVariant,
          backgroundColor: active ? colors.secondaryContainer : 'transparent',
        },
      ]}>
      <Checkbox
        checked={done}
        onPress={onToggleDone}
        label={`${done ? '取消完成' : '完成'}：${task.title}`}
      />

      <Pressable
        accessibilityRole={onOpen ? 'button' : undefined}
        accessibilityLabel={onOpen ? `任务详情：${task.title}` : task.title}
        onPress={onOpen}
        disabled={!onOpen}
        onFocus={onFocus}
        onBlur={onBlur}
        style={[
          styles.content,
          {
            boxShadow: focused ? `inset 0 0 0 2px ${colors.focusRing}` : undefined,
          },
        ]}>
        <Text
          style={[
            styles.title,
            {
              color: done || skipped ? colors.inkMuted : colors.ink,
              textDecorationLine: done ? 'line-through' : 'none',
            },
          ]}>
          {task.title}
        </Text>
        <View style={styles.metaRow}>
          <TaskMeta task={task} />
          {isClosed(task) ? (
            <Text style={[styles.tag, { color: task.done ? colors.primary : colors.warning }]}>
              {task.done ? '已完成' : '已跳过'}
            </Text>
          ) : null}
        </View>
      </Pressable>

      <Text style={[styles.duration, { color: colors.inkMuted }]}>
        {task.estimatedMinutes != null ? `${task.estimatedMinutes} 分钟` : '—'}
      </Text>

      {onOpen ? <DotsButton label={`任务详情：${task.title}`} onPress={onOpen} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
    minHeight: 64,
    paddingVertical: Space.sm,
    borderBottomWidth: 1,
  },
  content: {
    flex: 1,
    gap: 2,
    minWidth: 0,
    borderRadius: Radius.sm,
    paddingVertical: Space.xs,
  },
  title: {
    fontSize: Type.bodyLarge,
    lineHeight: Type.bodyLarge * Line.normal,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  tag: {
    fontSize: Type.labelSmall,
    fontWeight: '600',
  },
  duration: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
    minWidth: 52,
    textAlign: 'right',
  },
});
