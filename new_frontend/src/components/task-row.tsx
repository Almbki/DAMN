import {
  Pressable,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { DotsButton } from '@/components/task/dots-button';
import { TaskMeta } from '@/components/task-meta';
import { IconButton } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Icon } from '@/components/ui/icon';
import { useInteraction } from '@/components/ui/interaction';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { isClosed, type Task, type TaskStandard } from '@/domain/task';
import { useTheme } from '@/state/theme';

type Props = {
  task: Task;
  /** Keyboard/roving highlight. */
  active?: boolean;
  /** Whether the plan allows edits (start + substep checkboxes). */
  canEdit?: boolean;
  /** Substeps panel open state. */
  expanded?: boolean;
  onToggleDone: () => void;
  /** Opens the task detail sheet. */
  onOpen?: () => void;
  onStartTask?: () => void;
  onToggleExpanded?: () => void;
  onUpdateStandard?: (taskId: number, standardId: number, completed: boolean) => Promise<void>;
};

/**
 * A Material 3 list row. The row is a plain container; the checkbox, the
 * content button and the action cluster are siblings (nesting pressables emits
 * invalid HTML on react-native-web).
 */
export function TaskRow({
  task,
  active = false,
  canEdit = true,
  expanded = false,
  onToggleDone,
  onOpen,
  onStartTask,
  onToggleExpanded,
  onUpdateStandard,
}: Props) {
  const { colors } = useTheme();
  const { focused, onFocus, onBlur } = useInteraction();
  const done = task.done;
  const skipped = task.skipped;
  const closed = isClosed(task);
  const hasStandards = task.standards.length > 0;
  const started = task.startedAt != null;

  return (
    <View
      style={[
        styles.wrapper,
        {
          borderBottomColor: colors.outlineVariant,
          backgroundColor: active ? colors.secondaryContainer : 'transparent',
        },
      ]}>
      <View style={styles.row}>
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

        <TaskRowActions
          title={task.title}
          startable={canEdit && !closed && !started}
          started={!closed && started}
          hasStandards={hasStandards}
          expanded={expanded}
          onStart={onStartTask}
          onToggleExpanded={onToggleExpanded}
          onOpen={onOpen}
        />
      </View>

      {expanded && hasStandards ? (
        <SubstepsPanel
          standards={task.standards}
          disabled={closed || !canEdit || onUpdateStandard == null}
          onToggle={
            onUpdateStandard
              ? (standardId, completed) => {
                  void onUpdateStandard(task.id, standardId, completed);
                }
              : undefined
          }
          style={styles.substepsInset}
        />
      ) : null}
    </View>
  );
}

/**
 * The row's fast actions, ordered start/status → substeps → overflow. Shared by
 * the timeline and week rows so the interaction stays identical.
 */
export function TaskRowActions({
  title,
  startable = false,
  started = false,
  hasStandards = false,
  expanded = false,
  onStart,
  onToggleExpanded,
  onOpen,
}: {
  title: string;
  /** Caller decides permission and open state; this only draws the affordance. */
  startable?: boolean;
  started?: boolean;
  hasStandards?: boolean;
  expanded?: boolean;
  onStart?: () => void;
  onToggleExpanded?: () => void;
  onOpen?: () => void;
}) {
  const showStart = startable && !started && onStart != null;
  const showArrow = hasStandards && onToggleExpanded != null;

  if (!showStart && !started && !showArrow && onOpen == null) return null;

  return (
    <View style={styles.actions}>
      {showStart ? <RowStartButton title={title} onPress={onStart} /> : null}
      {started ? <RowInProgress title={title} /> : null}
      {showArrow ? (
        <IconButton
          name={expanded ? 'chevronDown' : 'chevronRight'}
          label={`${expanded ? '收起子步骤' : '展开子步骤'}：${title}`}
          size={36}
          selected={expanded}
          onPress={onToggleExpanded}
        />
      ) : null}
      {onOpen ? <DotsButton label={`任务详情：${title}`} onPress={onOpen} /> : null}
    </View>
  );
}

/** Compact tonal start pill; the label drops on narrow phones so the title keeps room. */
function RowStartButton({ title, onPress }: { title: string; onPress: () => void }) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const { width } = useWindowDimensions();
  const showLabel = width > 0 && width >= 420;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`开始任务：${title}`}
      onPress={onPress}
      {...handlers}
      style={({ pressed }) => [
        styles.startButton,
        {
          backgroundColor:
            hovered || pressed ? colors.primaryContainer : colors.secondaryContainer,
          opacity: pressed ? 0.9 : 1,
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      <Icon
        name="arrowRight"
        size={13}
        color={colors.onSecondaryContainer}
        strokeWidth={2.2}
      />
      {showLabel ? (
        <Text style={[styles.startLabel, { color: colors.onSecondaryContainer }]}>开始</Text>
      ) : null}
    </Pressable>
  );
}

function RowInProgress({ title }: { title: string }) {
  const { colors } = useTheme();
  return (
    <View accessible accessibilityLabel={`进行中：${title}`} style={styles.inProgress}>
      <View style={[styles.inProgressDot, { backgroundColor: colors.primary }]} />
      <Text style={[styles.inProgressText, { color: colors.inkMuted }]}>进行中</Text>
    </View>
  );
}

/** Expanded substeps live below the row content, never inside the row Pressable. */
export function SubstepsPanel({
  standards,
  onToggle,
  disabled = false,
  style,
}: {
  standards: TaskStandard[];
  onToggle?: (standardId: number, completed: boolean) => void;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors } = useTheme();
  const ordered = [...standards].sort((a, b) => a.orderIndex - b.orderIndex);

  if (ordered.length === 0) return null;

  return (
    <View style={[styles.substeps, { borderTopColor: colors.outlineVariant }, style]}>
      {ordered.map((standard) => (
        <View
          key={standard.id}
          style={[styles.substepRow, { opacity: disabled ? 0.68 : 1 }]}>
          <Checkbox
            checked={standard.completed}
            disabled={disabled || onToggle == null}
            label={`${standard.completed ? '取消完成' : '完成'}：${standard.description}`}
            onPress={() => onToggle?.(standard.id, !standard.completed)}
          />
          <Text
            style={[
              styles.substepText,
              {
                color: standard.completed ? colors.inkMuted : colors.ink,
                textDecorationLine: standard.completed ? 'line-through' : 'none',
              },
            ]}>
            {standard.description}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    borderBottomWidth: 1,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
    minHeight: 64,
    paddingVertical: Space.sm,
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
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    flexShrink: 0,
  },
  startButton: {
    height: 34,
    minWidth: 30,
    paddingHorizontal: Space.sm,
    borderRadius: Radius.pill,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
  },
  startLabel: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  inProgress: {
    height: 34,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 2,
  },
  inProgressDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  inProgressText: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  substeps: {
    borderTopWidth: 1,
    paddingBottom: Space.xs,
  },
  substepsInset: {
    paddingLeft: Space.sm,
  },
  substepRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
    paddingRight: Space.sm,
  },
  substepText: {
    flex: 1,
    minWidth: 0,
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.normal,
  },
});
