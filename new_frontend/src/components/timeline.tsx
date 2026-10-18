import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DotsButton } from '@/components/task/dots-button';
import { TaskKindBadge } from '@/components/task/task-kind-badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Icon } from '@/components/ui/icon';
import { useInteraction } from '@/components/ui/interaction';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import type { TaskKind } from '@/domain/task';
import { useTheme } from '@/state/theme';

/** Minimal shape the timeline draws — real tasks and preview drafts both map to it. */
export type TimelineItem = {
  id: number;
  title: string;
  done: boolean;
  /** Soft defer; drawn as a neutral tag, not as completion. */
  skipped?: boolean;
  startTime: string | null;
  endTime: string | null;
  estimatedMinutes: number | null;
  /** 1 low · 2 medium · 3 high */
  priority: number;
  /** Optional kind marker; preview drafts may omit it. */
  taskKind?: TaskKind;
  seriesIndex?: number | null;
  occurrenceDate?: string | null;
};

export function Timeline({
  items,
  interactive = true,
  nowId = null,
  activeId = null,
  onToggleDone,
  onOpen,
}: {
  items: TimelineItem[];
  /** Read-only (preview) when false: no checkbox, no overflow, no open. */
  interactive?: boolean;
  /** The current node, drawn in the live scallion tone. */
  nowId?: number | null;
  activeId?: number | null;
  onToggleDone?: (id: number) => void;
  /** Open the task detail sheet. The visible overflow uses the same action. */
  onOpen?: (id: number) => void;
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
          isNow={item.id === nowId}
          active={item.id === activeId}
          onToggleDone={onToggleDone}
          onOpen={onOpen}
        />
      ))}
    </View>
  );
}

function TimelineRow({
  item,
  interactive,
  isNow,
  active,
  onToggleDone,
  onOpen,
}: {
  item: TimelineItem;
  interactive: boolean;
  isNow: boolean;
  active: boolean;
  onToggleDone?: (id: number) => void;
  onOpen?: (id: number) => void;
}) {
  const { colors } = useTheme();
  const { focused, onFocus, onBlur } = useInteraction();
  const done = item.done;
  const skipped = item.skipped === true;
  const clickable = interactive && onOpen != null;

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
            disabled={!interactive}
            label={`${done ? '取消完成' : '完成'}：${item.title}`}
            onPress={() => interactive && onToggleDone?.(item.id)}
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
              <PriorityFlag priority={item.priority} />
            </View>
          </Pressable>

          {clickable ? (
            <DotsButton label={`任务详情：${item.title}`} onPress={() => onOpen?.(item.id)} />
          ) : null}
        </View>
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
  priority: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  priorityText: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
});
