import { Pressable, StyleSheet, Text, View } from 'react-native';

import { TaskKindBadge } from '@/components/task/task-kind-badge';
import { SubstepsPanel, TaskRowActions } from '@/components/task-row';
import { Checkbox } from '@/components/ui/checkbox';
import { Icon } from '@/components/ui/icon';
import { useInteraction } from '@/components/ui/interaction';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import type { TaskKind, TaskStandard } from '@/domain/task';
import { useTheme } from '@/state/theme';

/** Minimal shape the timeline draws — real tasks and preview drafts both map to it. */
export type TimelineItem = {
  id: number;
  title: string;
  done: boolean;
  /** Soft defer; drawn as a neutral tag, not as completion. */
  skipped?: boolean;
  /** Explicit backend backlog task, shown with a neutral 任务池 tag. */
  backlog?: boolean;
  startTime: string | null;
  endTime: string | null;
  estimatedMinutes: number | null;
  /** 1 low · 2 medium · 3 high */
  priority: number;
  /** Optional kind marker; preview drafts may omit it. */
  taskKind?: TaskKind;
  seriesIndex?: number | null;
  occurrenceDate?: string | null;
  /** Checklist items, when the row belongs to a persisted task. */
  standards?: TaskStandard[];
  /** Local start timestamp; drives the quiet "进行中" status. */
  startedAt?: string | null;
};

export function Timeline({
  items,
  interactive = true,
  canEdit = true,
  expandedIds,
  nowId = null,
  activeId = null,
  onToggleDone,
  onOpen,
  onStartTask,
  onToggleExpanded,
  onUpdateStandard,
}: {
  items: TimelineItem[];
  /** Read-only (preview) when false: no checkbox, no overflow, no open. */
  interactive?: boolean;
  /** Whether the plan allows edits (start + substep checkboxes). */
  canEdit?: boolean;
  /** Ids whose substeps panel is open. */
  expandedIds?: ReadonlySet<number>;
  /** The current node, drawn in the live scallion tone. */
  nowId?: number | null;
  activeId?: number | null;
  onToggleDone?: (id: number) => void;
  /** Open the task detail sheet. The visible overflow uses the same action. */
  onOpen?: (id: number) => void;
  onStartTask?: (id: number) => void;
  onToggleExpanded?: (id: number) => void;
  onUpdateStandard?: (
    taskId: number,
    standardId: number,
    completed: boolean,
  ) => Promise<void>;
}) {
  const ordered = [...items].sort((a, b) => {
    if (a.startTime && b.startTime) return a.startTime.localeCompare(b.startTime);
    if (a.startTime) return -1;
    if (b.startTime) return 1;
    return a.id - b.id;
  });

  return (
    <View>
      {ordered.map((item) => (
        <TimelineRow
          key={item.id}
          item={item}
          interactive={interactive}
          canEdit={canEdit}
          expanded={expandedIds?.has(item.id) === true}
          isNow={item.id === nowId}
          active={item.id === activeId}
          onToggleDone={onToggleDone}
          onOpen={onOpen}
          onStartTask={onStartTask}
          onToggleExpanded={onToggleExpanded}
          onUpdateStandard={onUpdateStandard}
        />
      ))}
    </View>
  );
}

function TimelineRow({
  item,
  interactive,
  canEdit,
  expanded,
  isNow,
  active,
  onToggleDone,
  onOpen,
  onStartTask,
  onToggleExpanded,
  onUpdateStandard,
}: {
  item: TimelineItem;
  interactive: boolean;
  canEdit: boolean;
  expanded: boolean;
  isNow: boolean;
  active: boolean;
  onToggleDone?: (id: number) => void;
  onOpen?: (id: number) => void;
  onStartTask?: (id: number) => void;
  onToggleExpanded?: (id: number) => void;
  onUpdateStandard?: (
    taskId: number,
    standardId: number,
    completed: boolean,
  ) => Promise<void>;
}) {
  const { colors } = useTheme();
  const { focused, onFocus, onBlur } = useInteraction();
  const done = item.done;
  const skipped = item.skipped === true;
  const closed = done || skipped;
  const clickable = interactive && onOpen != null;
  const standards = item.standards ?? [];
  const hasStandards = standards.length > 0;
  const expandedPanel = expanded && hasStandards;
  const started = item.startedAt != null;

  return (
    <View style={styles.row}>
      <View style={styles.timeCol}>
        <Text style={[styles.time, { color: item.startTime ? colors.inkMuted : colors.inkFaint }]}>
          {item.startTime ?? '—'}
        </Text>
      </View>

      <View style={styles.axis}>
        <View style={[styles.axisLine, { backgroundColor: colors.outlineVariant }]} />
        <View
          style={[
            styles.node,
            isNow
              ? { width: 14, height: 14, borderRadius: 7, backgroundColor: colors.now }
              : done
                ? { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.ink }
                : {
                    width: 10,
                    height: 10,
                    borderRadius: 5,
                    borderWidth: 2,
                    borderColor: colors.outline,
                    backgroundColor: colors.surfaceContainerLowest,
                  },
          ]}
        />
      </View>

      <Surface
        level={active ? 'level2' : 'level1'}
        radius="lg"
        style={[
          styles.card,
          { borderColor: focused ? colors.focusRing : 'transparent', borderWidth: 1 },
        ]}>
        <View style={styles.cardRow}>
          <Checkbox
            checked={done}
            disabled={!interactive || !canEdit}
            label={`${done ? '取消完成' : '完成'}：${item.title}`}
            onPress={() => interactive && canEdit && onToggleDone?.(item.id)}
          />

          <Pressable
            accessibilityRole={clickable ? 'button' : undefined}
            accessibilityLabel={clickable ? `任务详情：${item.title}` : item.title}
            disabled={!clickable}
            onPress={clickable ? () => onOpen?.(item.id) : undefined}
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
              {item.title}
            </Text>
            <View style={styles.metaRow}>
              {item.taskKind && item.taskKind !== 'one_off' ? (
                <TaskKindBadge
                  taskKind={item.taskKind}
                  seriesIndex={item.seriesIndex ?? null}
                  occurrenceDate={item.occurrenceDate ?? null}
                />
              ) : null}
              {item.startTime ? (
                <Text style={[styles.range, { color: colors.inkMuted }]}>
                  {item.startTime}
                  {item.endTime ? ` - ${item.endTime}` : ''}
                </Text>
              ) : null}
              {item.estimatedMinutes ? (
                <Text style={[styles.range, { color: colors.inkMuted }]}>
                  {item.startTime ? '· ' : '约 '}
                  {item.estimatedMinutes} 分钟
                </Text>
              ) : null}
              {skipped ? (
                <Text style={[styles.skipped, { color: colors.warning }]}>已跳过</Text>
              ) : null}
              {item.backlog === true ? (
                <Text style={[styles.backlog, { color: colors.inkMuted }]}>任务池</Text>
              ) : null}
              <PriorityFlag priority={item.priority} />
            </View>
          </Pressable>

          <TaskRowActions
            title={item.title}
            startable={interactive && canEdit && !closed && !started && onStartTask != null}
            started={interactive && !closed && started}
            hasStandards={hasStandards}
            expanded={expandedPanel}
            onStart={onStartTask ? () => onStartTask(item.id) : undefined}
            onToggleExpanded={
              interactive && onToggleExpanded
                ? () => onToggleExpanded(item.id)
                : undefined
            }
            onOpen={clickable ? () => onOpen?.(item.id) : undefined}
          />
        </View>

        {expandedPanel ? (
          <SubstepsPanel
            standards={standards}
            disabled={closed || !canEdit || onUpdateStandard == null}
            onToggle={
              onUpdateStandard
                ? (standardId, completed) => {
                    void onUpdateStandard(item.id, standardId, completed);
                  }
                : undefined
            }
            style={styles.substepsInset}
          />
        ) : null}
      </Surface>
    </View>
  );
}

function PriorityFlag({ priority }: { priority: number }) {
  const { colors } = useTheme();
  const tone = priority >= 3 ? colors.error : priority === 2 ? colors.warning : colors.inkMuted;
  const label = priority >= 3 ? '高' : priority === 2 ? '中' : '低';
  return (
    <View style={styles.priority}>
      <Icon name="flag" size={14} color={tone} strokeWidth={1.6} />
      <Text style={[styles.priorityText, { color: tone }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'stretch',
    minHeight: 76,
  },
  timeCol: {
    width: 52,
    paddingTop: Space.lg,
    alignItems: 'flex-end',
    paddingRight: Space.sm,
  },
  time: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  axis: {
    width: 20,
    alignItems: 'center',
  },
  axisLine: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 2,
  },
  node: {
    marginTop: Space.lg + 4,
  },
  card: {
    flex: 1,
    marginLeft: Space.sm,
    marginVertical: Space.xs,
    minWidth: 0,
  },
  cardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
    paddingHorizontal: Space.sm,
    paddingVertical: Space.sm,
  },
  content: {
    flex: 1,
    gap: Space.xs,
    minWidth: 0,
    borderRadius: Radius.sm,
    paddingVertical: Space.xs,
  },
  title: {
    fontSize: Type.bodyLarge,
    fontWeight: '500',
    lineHeight: Type.bodyLarge * Line.normal,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    flexWrap: 'wrap',
  },
  range: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  skipped: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  backlog: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  priority: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  priorityText: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  substepsInset: {
    paddingLeft: Space.sm,
  },
});
