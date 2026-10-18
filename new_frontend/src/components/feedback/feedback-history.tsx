import { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { taskReasonLabel } from '@/components/feedback/reasons';
import { Surface } from '@/components/ui/surface';
import type { FeedbackRead } from '@/api/types';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import type { Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

/** The last several submissions: auto rate, energy/stress, per-task reasons. */
export function FeedbackHistory({
  history,
  tasks,
}: {
  history: FeedbackRead[];
  tasks: Task[];
}) {
  const { colors } = useTheme();
  const titleById = useMemo(
    () => new Map(tasks.map((task) => [task.id, task.title])),
    [tasks],
  );
  const rows = useMemo(
    () =>
      [...history]
        .sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id)
        .slice(0, 6),
    [history],
  );

  return (
    <View style={styles.section}>
      <View style={styles.sectionHead}>
        <Text style={[styles.sectionTitle, { color: colors.ink }]}>最近反馈</Text>
        <Text style={[styles.counter, { color: colors.inkMuted }]}>
          {history.length > 0 ? `${history.length} 条` : '暂无'}
        </Text>
      </View>

      {rows.length === 0 ? (
        <Surface level="level0" radius="lg" bordered style={{ borderStyle: 'dashed' }}>
          <View style={styles.empty}>
            <Text style={[styles.emptyTitle, { color: colors.ink }]}>还没有反馈记录</Text>
            <Text style={[styles.helper, { color: colors.inkMuted }]}>
              提交后，日期、自动完成率、精力和压力会留在这里，方便回看这一周的状态。
            </Text>
          </View>
        </Surface>
      ) : (
        rows.map((item) => {
          const reasons = item.task_reasons ?? [];
          const levels = [
            item.energy_level != null ? `精力 ${item.energy_level}` : null,
            item.stress_level != null ? `压力 ${item.stress_level}` : null,
          ]
            .filter(Boolean)
            .join(' · ');

          return (
            <View
              key={`${item.id}-${item.date}`}
              style={[styles.row, { borderTopColor: colors.outlineVariant }]}>
              <View style={styles.rowHead}>
                <Text style={[styles.date, { color: colors.inkMuted }]}>
                  {item.date.slice(0, 10)}
                </Text>
                <Text style={[styles.rate, { color: colors.ink }]}>
                  {Math.round((item.completion_rate ?? 0) * 100)}%
                </Text>
                <Text style={[styles.levels, { color: colors.inkMuted }]}>
                  {levels || '未填状态'}
                </Text>
              </View>

              {reasons.length > 0 ? (
                <View style={styles.reasonList}>
                  {reasons.map((reason, index) => {
                    const taskTitle = titleById.get(reason.task_id) ?? `任务 #${reason.task_id}`;
                    const note = reason.note ? `（${reason.note}）` : '';
                    return (
                      <View
                        key={`${reason.task_id}-${reason.reason}-${index}`}
                        style={[
                          styles.reasonPill,
                          {
                            backgroundColor: colors.surfaceContainerLow,
                            borderColor: colors.outlineVariant,
                          },
                        ]}>
                        <Text style={[styles.reasonText, { color: colors.inkMuted }]}>
                          {taskTitle} · {taskReasonLabel(reason.reason)}
                          {note}
                        </Text>
                      </View>
                    );
                  })}
                </View>
              ) : (
                <Text style={[styles.helper, { color: colors.inkFaint }]}>
                  没有记录具体原因
                </Text>
              )}

              {item.free_text ? (
                <Text style={[styles.freeText, { color: colors.ink }]}>{item.free_text}</Text>
              ) : null}
            </View>
          );
        })
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: Space.sm,
  },
  sectionHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  sectionTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  counter: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  empty: {
    padding: Space.lg,
    gap: Space.xs,
  },
  emptyTitle: {
    fontSize: Type.bodyLarge,
    fontWeight: '600',
  },
  helper: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  row: {
    borderTopWidth: 1,
    paddingVertical: Space.md,
    gap: Space.sm,
  },
  rowHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  date: {
    fontFamily: Fonts.mono,
    fontSize: Type.labelMedium,
    minWidth: 88,
  },
  rate: {
    fontFamily: Fonts.mono,
    fontSize: Type.bodyLarge,
    minWidth: 48,
  },
  levels: {
    flexGrow: 1,
    fontSize: Type.labelMedium,
  },
  reasonList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.xs,
  },
  reasonPill: {
    borderWidth: 1,
    borderRadius: Radius.pill,
    paddingHorizontal: Space.md,
    paddingVertical: Space.xs,
  },
  reasonText: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
  },
  freeText: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.normal,
  },
});
