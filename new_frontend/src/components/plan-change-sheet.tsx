import { StyleSheet, Text, View } from 'react-native';

import { BottomSheet } from '@/components/ui/bottom-sheet';
import { Icon } from '@/components/ui/icon';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { formatShort } from '@/domain/date';
import type { PlanChange, PlanChangeDay } from '@/domain/plan-change';
import { useTheme } from '@/state/theme';

const TRIGGER_LABEL: Record<string, string> = {
  manual: '手动重排',
  feedback_triggered: '反馈触发',
  scheduled: '定时重排',
  system: '系统调整',
};

/**
 * "The system changed your next few days" — the plan-change notice. Per-day
 * `taskIds` are counted here so a day with no changed task ids is visibly empty
 * rather than implied to have changed.
 */
export function PlanChangeSheet({
  visible,
  changes,
  onClose,
}: {
  visible: boolean;
  changes: PlanChange[];
  onClose: () => void;
}) {
  const { colors } = useTheme();

  return (
    <BottomSheet
      visible={visible}
      title="计划变更"
      subtitle="每次重排都会生成新版本，旧版本保留。这里记录系统动过哪些天。"
      onClose={onClose}>
      {changes.length === 0 ? (
        <Surface level="level0" radius="lg" bordered style={{ borderStyle: 'dashed' }}>
          <View style={styles.empty}>
            <Text style={[styles.emptyTitle, { color: colors.ink }]}>还没有计划变更</Text>
            <Text style={[styles.body, { color: colors.inkMuted }]}>
              手动重排或完成反馈触发重排后，这里会列出被改动的日期和任务数。
            </Text>
          </View>
        </Surface>
      ) : (
        changes.map((change, changeIndex) => {
          const affected = new Set(change.days.flatMap((day) => day.taskIds)).size;
          return (
            <View key={`${change.id}-${changeIndex}`} style={styles.change}>
              <View style={styles.changeHead}>
                <View style={styles.changeTitleBlock}>
                  <Text style={[styles.reason, { color: colors.ink }]}>
                    {change.reason || TRIGGER_LABEL[change.triggerType] || '系统重排'}
                  </Text>
                  <Text style={[styles.meta, { color: colors.inkFaint }]}>
                    {TRIGGER_LABEL[change.triggerType] ?? change.triggerType}
                    {change.createdAt ? ` · ${change.createdAt.slice(0, 10)}` : ''}
                    {affected > 0 ? ` · 涉及 ${affected} 个任务` : ' · 没有任务被移动'}
                  </Text>
                </View>
                <Text style={[styles.version, { color: colors.inkFaint }]}>
                  v{change.oldVersion} → v{change.newVersion}
                </Text>
              </View>

              <View style={styles.days}>
                {change.days.length === 0 ? (
                  <Text style={[styles.body, { color: colors.inkMuted }]}>
                    这次重排没有按天记录改动。
                  </Text>
                ) : (
                  change.days.map((day, dayIndex) => (
                    <DayRow
                      key={`${change.id}-${day.date}-${dayIndex}`}
                      day={day}
                    />
                  ))
                )}
              </View>
            </View>
          );
        })
      )}
    </BottomSheet>
  );
}

function DayRow({ day }: { day: PlanChangeDay }) {
  const { colors } = useTheme();
  const affected = day.taskIds.length;
  return (
    <Surface level="level0" radius="md" tone="low">
      <View style={styles.day}>
        <View style={styles.dayHead}>
          <Text style={[styles.dayDate, { color: colors.ink }]}>{formatShort(day.date)}</Text>
          <View style={styles.dayTags}>
            {day.added > 0 ? <Tag label={`新增 ${day.added}`} tone={colors.primary} /> : null}
            {day.moved > 0 ? <Tag label={`移动 ${day.moved}`} tone={colors.inkMuted} /> : null}
            {day.removed > 0 ? <Tag label={`移除 ${day.removed}`} tone={colors.error} /> : null}
            {affected > 0 ? <Tag label={`涉及 ${affected} 个`} tone={colors.inkFaint} /> : null}
          </View>
        </View>
        <View style={styles.summaryRow}>
          <Icon name="arrowRight" size={14} color={colors.inkFaint} />
          <Text style={[styles.summary, { color: colors.inkMuted }]}>
            {day.summary || '这一天的安排有调整。'}
          </Text>
        </View>
      </View>
    </Surface>
  );
}

function Tag({ label, tone }: { label: string; tone: string }) {
  return (
    <Text style={[styles.tag, { color: tone, borderColor: tone }]} accessibilityLabel={label}>
      {label}
    </Text>
  );
}

const styles = StyleSheet.create({
  empty: {
    padding: Space.xl,
    gap: Space.sm,
  },
  emptyTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
  },
  change: {
    gap: Space.md,
  },
  changeHead: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  changeTitleBlock: {
    flex: 1,
    gap: 2,
  },
  reason: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  meta: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
  },
  version: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  days: {
    gap: Space.sm,
  },
  day: {
    padding: Space.md,
    gap: Space.sm,
  },
  dayHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  dayDate: {
    fontSize: Type.bodyLarge,
    fontWeight: '600',
  },
  dayTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.xs,
    justifyContent: 'flex-end',
  },
  tag: {
    borderWidth: 1,
    borderRadius: Radius.pill,
    paddingHorizontal: Space.sm,
    paddingVertical: 2,
    fontSize: Type.labelSmall,
    overflow: 'hidden',
  },
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  summary: {
    flex: 1,
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.normal,
  },
});
