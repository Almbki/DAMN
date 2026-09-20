import { Pressable, StyleSheet, Text, View } from 'react-native';

import { TaskMeta } from '@/components/task-meta';
import { useInteraction } from '@/components/ui/interaction';
import { Line, Radius, Space, Type } from '@/constants/tokens';
import { isClosed, type Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

type Props = {
  task: Task;
  active?: boolean;
  selected?: boolean;
  batchMode?: boolean;
  dragging?: boolean;
  draggable?: boolean;
  onToggleDone: () => void;
  onOpen: () => void;
  onToggleSelect: () => void;
  onSkip: () => void;
  onDragStart?: () => void;
  onDragEnter?: () => void;
  onDragEnd?: () => void;
};

/**
 * The row is a plain container; every control is a sibling button. Nesting
 * pressables would emit real `<button>` inside `<button>` on web (RNW renders
 * `accessibilityRole="button"` as a native button element).
 */
export function TaskRow({
  task,
  active = false,
  selected = false,
  batchMode = false,
  dragging = false,
  draggable = false,
  onToggleDone,
  onOpen,
  onToggleSelect,
  onSkip,
  onDragStart,
  onDragEnter,
  onDragEnd,
}: Props) {
  const { colors } = useTheme();
  const { focused, hovered, onFocus, onBlur, onHoverIn, onHoverOut } = useInteraction();
  const done = isClosed(task);
  const marked = batchMode ? selected : done;
  const ringed = focused || active;

  return (
    <View
      onPointerEnter={() => {
        onHoverIn();
        if (dragging) onDragEnter?.();
      }}
      onPointerLeave={onHoverOut}
      style={[
        styles.row,
        {
          borderBottomColor: colors.line,
          backgroundColor: dragging ? colors.pressed : hovered || active ? colors.hover : 'transparent',
          boxShadow: ringed ? `inset 0 0 0 2px ${colors.lineStrong}` : undefined,
          opacity: dragging ? 0.6 : 1,
        },
      ]}>
      <Pressable
        accessibilityRole="checkbox"
        accessibilityState={{ checked: marked }}
        accessibilityLabel={`${batchMode ? '选择' : '完成'}：${task.title}`}
        onPress={batchMode ? onToggleSelect : onToggleDone}
        onFocus={onFocus}
        onBlur={onBlur}
        style={[
          styles.checkbox,
          { borderColor: colors.ink, backgroundColor: marked ? colors.ink : 'transparent' },
        ]}>
        {marked ? <Text style={[styles.checkGlyph, { color: colors.onInk }]}>✓</Text> : null}
      </Pressable>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`打开任务：${task.title}`}
        onPress={batchMode ? onToggleSelect : onOpen}
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

      {hovered && !done && !batchMode ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`今天先不做：${task.title}`}
          onPress={onSkip}
          style={styles.rowAction}>
          <Text style={[styles.rowActionText, { color: colors.mintInk }]}>今天先不做</Text>
        </Pressable>
      ) : null}

      <Text style={[styles.duration, { color: colors.inkMuted }]}>{task.estimatedMinutes ?? '—'}</Text>

      {draggable && !batchMode ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`拖动排序：${task.title}`}
          onPointerDown={onDragStart}
          onPointerUp={onDragEnd}
          onPointerCancel={onDragEnd}
          style={styles.handle}>
          <Text style={[styles.handleText, { color: colors.inkFaint }]}>≡</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    minHeight: 56,
    paddingVertical: Space.md,
    borderBottomWidth: 1,
  },
  checkbox: {
    width: 20,
    height: 20,
    borderRadius: Radius.sm,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkGlyph: {
    fontSize: Type.small,
    lineHeight: Type.small * 1.1,
    fontWeight: '700',
  },
  content: {
    flex: 1,
    gap: Space.xs,
    minWidth: 0,
  },
  title: {
    fontSize: Type.body,
    lineHeight: Type.body * Line.normal,
  },
  rowAction: {
    paddingHorizontal: Space.sm,
    minHeight: 32,
    justifyContent: 'center',
  },
  rowActionText: {
    fontSize: Type.small,
  },
  duration: {
    fontSize: Type.small,
    fontFamily: 'IBMPlexMono_400Regular',
    minWidth: 28,
    textAlign: 'right',
  },
  handle: {
    paddingHorizontal: Space.sm,
    minHeight: 32,
    justifyContent: 'center',
  },
  handleText: {
    fontSize: Type.body,
  },
});
