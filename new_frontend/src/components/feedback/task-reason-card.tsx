import { StyleSheet, Text, View } from 'react-native';

import { TASK_REASON_OPTIONS, taskReasonLabel } from '@/components/feedback/reasons';
import { Button } from '@/components/ui/button';
import { FilterChip } from '@/components/ui/chip';
import { Surface } from '@/components/ui/surface';
import { TextField } from '@/components/ui/text-field';
import { Line, Radius, Space, Type } from '@/constants/tokens';
import type { Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

/**
 * One unfinished task: the title, why it still needs a reason, the reason
 * chips, and an optional note once a reason is selected.
 */
export function TaskReasonCard({
  task,
  reason,
  note,
  missing,
  onReasonChange,
  onNoteChange,
  onComplete,
}: {
  task: Task;
  reason: string;
  note: string;
  missing: boolean;
  onReasonChange: (reason: string) => void;
  onNoteChange: (note: string) => void;
  /** Optional fast completion; only open tasks receive this. */
  onComplete?: () => void;
}) {
  const { colors } = useTheme();
  const planned = task.estimatedMinutes ?? task.predictedDuration;
  const completedStandards = task.standards.filter((standard) => standard.completed).length;
  const meta = [
    task.skipped ? '今天先不做' : null,
    planned != null ? `计划 ${planned} 分` : null,
    task.actualMinutes != null ? `实际 ${task.actualMinutes} 分` : null,
    task.standards.length > 0 ? `标准 ${completedStandards}/${task.standards.length}` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <Surface
      level="level0"
      radius="lg"
      bordered
      style={{ borderColor: missing ? colors.warning : colors.outlineVariant }}>
      <View style={styles.card}>
        <View style={styles.head}>
          <Text style={[styles.title, { color: colors.ink }]}>{task.title}</Text>
          <View style={styles.headActions}>
            {task.skipped ? (
              <View style={[styles.badge, { backgroundColor: colors.warningContainer }]}>
                <Text style={[styles.badgeText, { color: colors.onWarningContainer }]}>已跳过</Text>
              </View>
            ) : null}
            {onComplete ? (
              <Button
                label="已完成"
                variant="filled"
                size="sm"
                icon="check"
                onPress={onComplete}
              />
            ) : null}
          </View>
        </View>

        {meta ? <Text style={[styles.meta, { color: colors.inkMuted }]}>{meta}</Text> : null}

        <View style={styles.reasonBlock}>
          <View style={styles.reasonHead}>
            <Text style={[styles.reasonLabel, { color: colors.inkMuted }]}>没做完的原因</Text>
            {missing ? (
              <Text accessibilityLiveRegion="polite" style={[styles.missing, { color: colors.warning }]}>
                请选一个
              </Text>
            ) : (
              <Text style={[styles.chosen, { color: colors.primary }]}>
                {taskReasonLabel(reason)}
              </Text>
            )}
          </View>

          <View style={styles.chips}>
            {TASK_REASON_OPTIONS.map((option) => (
              <FilterChip
                key={option.key}
                label={option.label}
                selected={reason === option.key}
                onPress={() => onReasonChange(option.key)}
              />
            ))}
          </View>
        </View>

        {reason ? (
          <TextField
            label={reason === 'other' ? '其他原因说明（可选）' : '备注（可选）'}
            value={note}
            onChangeText={onNoteChange}
            placeholder={reason === 'other' ? '比如：临时被叫走' : '想补充的话'}
            background={colors.surfaceContainerLowest}
          />
        ) : null}
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: Space.lg,
    gap: Space.md,
  },
  head: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  title: {
    flex: 1,
    minWidth: 0,
    fontSize: Type.bodyLarge,
    lineHeight: Type.bodyLarge * Line.normal,
    fontWeight: '600',
  },
  headActions: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  badge: {
    borderRadius: Radius.pill,
    paddingHorizontal: Space.sm,
    paddingVertical: 2,
  },
  badgeText: {
    fontSize: Type.labelSmall,
    fontWeight: '600',
  },
  meta: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  reasonBlock: {
    gap: Space.sm,
  },
  reasonHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  reasonLabel: {
    fontSize: Type.labelMedium,
  },
  missing: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  chosen: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
});
