import { Pressable, StyleSheet, Text, View } from 'react-native';

import { TaskMeta } from '@/components/task-meta';
import { Checkbox } from '@/components/ui/checkbox';
import { useInteraction } from '@/components/ui/interaction';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import { isClosed, type Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

type Props = {
  task: Task;
  /** Keyboard/roving highlight. */
  active?: boolean;
  onToggleDone: () => void;
  /** Absent in api mode, where the backend cannot edit tasks. */
  onOpen?: () => void;
  onSkip?: () => void;
};

/**
 * A Material 3 list row. The row is a plain container; the checkbox and the
 * optional action are sibling controls (nesting pressables emits invalid HTML
 * on react-native-web).
 */
export function TaskRow({ task, active = false, onToggleDone, onOpen, onSkip }: Props) {
  const { colors } = useTheme();
  const { focused, hovered, onFocus, onBlur, onHoverIn, onHoverOut } = useInteraction();
  const done = isClosed(task);

  return (
    <View
      onPointerEnter={onHoverIn}
      onPointerLeave={onHoverOut}
      style={[
        styles.row,
        {
          borderBottomColor: colors.outlineVariant,
          backgroundColor: active ? colors.secondaryContainer : hovered ? colors.hover : 'transparent',
          boxShadow: focused ? `inset 0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      <Checkbox
        checked={done}
        onPress={onToggleDone}
        label={`${done ? '取消完成' : '完成'}：${task.title}`}
      />

      <Pressable
        accessibilityRole={onOpen ? 'button' : undefined}
        accessibilityLabel={onOpen ? `编辑任务：${task.title}` : task.title}
        onPress={onOpen}
        disabled={!onOpen}
        onFocus={onFocus}
        onBlur={onBlur}
        style={styles.content}>
        <Text
          style={[
            styles.title,
            {
              color: done ? colors.inkMuted : colors.ink,
              textDecorationLine: done ? 'line-through' : 'none',
            },
          ]}>
          {task.title}
        </Text>
        <TaskMeta task={task} />
      </Pressable>

      {onSkip && !done && hovered ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`今天先不做：${task.title}`}
          onPress={onSkip}
          style={styles.rowAction}>
          <Text style={[styles.rowActionText, { color: colors.primary }]}>今天先不做</Text>
        </Pressable>
      ) : null}

      <Text style={[styles.duration, { color: colors.inkMuted }]}>
        {task.estimatedMinutes ?? '—'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
    minHeight: 64,
    paddingVertical: Space.sm,
    borderBottomWidth: 1,
  },
  content: {
    flex: 1,
    gap: 2,
    minWidth: 0,
    paddingVertical: Space.xs,
  },
  title: {
    fontSize: Type.bodyLarge,
    lineHeight: Type.bodyLarge * Line.normal,
  },
  rowAction: {
    paddingHorizontal: Space.sm,
    minHeight: 32,
    justifyContent: 'center',
  },
  rowActionText: {
    fontSize: Type.labelMedium,
  },
  duration: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
    minWidth: 28,
    textAlign: 'right',
  },
});
