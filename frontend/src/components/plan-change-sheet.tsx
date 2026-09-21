import { StyleSheet, Text, View } from 'react-native';

import { BottomSheet } from '@/components/ui/bottom-sheet';
import { Icon } from '@/components/ui/icon';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { formatShort } from '@/domain/date';
import type { PlanChange, PlanChangeDay } from '@/domain/plan-change';
import { useTheme } from '@/state/theme';

/**
 * "The system changed your next few days" — the plan-change notice. Data is
 * mocked until the backend exposes replan changes (docs/design/backend-api-gaps.md §1).
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
      subtitle="系统重排后，未来这些天被改动过。"
      onClose={onClose}>
      {changes.length === 0 ? (
        <Text style={[styles.empty, { color: colors.inkMuted }]}>
          还没有变更记录。系统会在反馈触发重排后记录在这里。
        </Text>
      ) : (
        changes.map((change) => (
          <View key={change.id} style={styles.change}>
            <View style={styles.changeHead}>
              <Text style={[styles.reason, { color: colors.ink }]}>{change.reason}</Text>
              <Text style={[styles.version, { color: colors.inkFaint }]}>
                v{change.oldVersion} → v{change.newVersion}
              </Text>
            </View>
            <View style={styles.days}>
              {change.days.map((day) => (
                <DayRow key={day.date} day={day} />
              ))}
            </View>
          </View>
        ))
      )}
    </BottomSheet>
  );
}

function DayRow({ day }: { day: PlanChangeDay }) {
  const { colors } = useTheme();
  return (
    <Surface level="level0" radius="md" tone="low">
      <View style={styles.day}>
        <View style={styles.dayHead}>
          <Text style={[styles.dayDate, { color: colors.ink }]}>{formatShort(day.date)}</Text>
          <View style={styles.dayTags}>
            {day.added > 0 ? <Tag label={`新增 ${day.added}`} tone={colors.primary} /> : null}
            {day.moved > 0 ? <Tag label={`移动 ${day.moved}`} tone={colors.inkMuted} /> : null}
            {day.removed > 0 ? <Tag label={`移除 ${day.removed}`} tone={colors.error} /> : null}
          </View>
        </View>
        <View style={styles.summaryRow}>
          <Icon name="arrowRight" size={14} color={colors.inkFaint} />
          <Text style={[styles.summary, { color: colors.inkMuted }]}>{day.summary}</Text>
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
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
  },
  change: {
    gap: Space.md,
  },
  changeHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  reason: {
    flex: 1,
    fontSize: Type.titleMedium,
    fontWeight: '600',
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
    gap: Space.xs,
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
