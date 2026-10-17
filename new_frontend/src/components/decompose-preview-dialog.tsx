import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Timeline, type TimelineItem } from '@/components/timeline';
import { Dialog } from '@/components/ui/dialog';
import { InlineNotice } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { TextField } from '@/components/ui/text-field';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { formatShort } from '@/domain/date';
import type { DraftTask } from '@/domain/decompose';
import type { DataMode } from '@/state/plan-context';
import { useTheme } from '@/state/theme';

function toItem(task: DraftTask): TimelineItem {
  return {
    id: task.id,
    title: task.title,
    done: false,
    startTime: task.startTime,
    endTime: task.endTime,
    estimatedMinutes: task.estimatedMinutes,
    priority: task.priority,
  };
}

/**
 * 拆解预览：把候选任务按天画成只读时间轴（照抄待办样式），下面留一个反馈框，
 * 可「重新生成」或「确认并生成计划」。真正的拆解由后端智能体完成，当前为本地模拟。
 */
export function DecomposePreviewDialog({
  tasks,
  mode,
  canAdjust,
  busy,
  message,
  stage,
  warnings = [],
  violations = [],
  estimatedTotalMinutes = 0,
  dailyLimitMinutes = null,
  error,
  onDismissError,
  onRegenerate,
  onConfirm,
  onClose,
}: {
  tasks: DraftTask[];
  mode: DataMode;
  canAdjust: boolean;
  busy: boolean;
  message: string | null;
  /** Human label for the currently streaming generation stage (optional). */
  stage?: string | null;
  warnings?: string[];
  /** Hard-rule violations from the backend, already human-readable. */
  violations?: string[];
  estimatedTotalMinutes?: number;
  dailyLimitMinutes?: number | null;
  error?: string | null;
  onDismissError?: () => void;
  onRegenerate: (feedback: string) => void;
  onConfirm: () => Promise<void> | void;
  onClose: () => void;
}) {
  const { colors } = useTheme();
  const [feedback, setFeedback] = useState('');
  const [closing, setClosing] = useState(false);

  const trimmedFeedback = feedback.trim();
  // The backend requires `feedback` to be non-empty (422 otherwise).
  const canRegenerate = canAdjust && !busy && trimmedFeedback.length > 0;

  const days = Array.from(new Set(tasks.map((task) => task.dueDate))).sort();

  function requestClose() {
    if (busy) return;
    setClosing(true);
  }

  return (
    <Dialog
      visible
      width={640}
      title="拆解预览"
      description={
        closing
          ? '关闭后需要重新拆解，当前这版预览和写下的反馈都不会保留。'
          : `共 ${tasks.length} 条，分布在 ${days.length} 天。预览仅供参考，不可编辑。`
      }
      closable={!busy}
      onRequestClose={requestClose}
      actions={
        closing
          ? [
              {
                label: '继续编辑',
                variant: 'tonal',
                onPress: () => setClosing(false),
              },
              {
                label: '关闭预览',
                variant: 'filled',
                onPress: onClose,
              },
            ]
          : [
              {
                label: canAdjust ? '重新生成' : '不能再调整',
                variant: 'tonal',
                disabled: !canRegenerate,
                onPress: () => onRegenerate(trimmedFeedback),
              },
              {
                label: busy ? '生成中…' : '确认并生成计划',
                variant: 'filled',
                disabled: busy,
                onPress: onConfirm,
              },
            ]
      }>
      <Surface level="level0" radius="md" bordered>
        <View style={styles.summary}>
          <Text style={[styles.summaryTitle, { color: colors.ink }]}>这次拆解</Text>
          <Text style={[styles.meta, { color: colors.inkMuted }]}>
            共 <Text style={styles.mono}>{tasks.length}</Text> 条 · 分布在{' '}
            <Text style={styles.mono}>{days.length}</Text> 天
          </Text>
          <Text style={[styles.meta, { color: colors.inkMuted }]}>
            预计总时长 <Text style={styles.mono}>{estimatedTotalMinutes}</Text> 分钟
            {dailyLimitMinutes != null ? (
              <>
                {' '}
                · 单日上限 <Text style={styles.mono}>{dailyLimitMinutes}</Text> 分钟
              </>
            ) : null}
          </Text>
          {busy && stage ? (
            <Text style={[styles.meta, { color: colors.primary }]}>拆解中 · {stage}</Text>
          ) : stage ? (
            <Text style={[styles.meta, { color: colors.primary }]}>当前阶段：{stage}</Text>
          ) : null}
        </View>
      </Surface>

      {violations.length > 0 ? (
        <View
          accessibilityRole="alert"
          style={[styles.alert, { backgroundColor: colors.errorContainer, borderColor: colors.error }]}>
          <Text style={[styles.alertTitle, { color: colors.onErrorContainer }]}>规则提醒</Text>
          {violations.map((violation, index) => (
            <Text
              key={`violation-${index}-${violation}`}
              style={[styles.alertText, { color: colors.onErrorContainer }]}>
              · {violation}
            </Text>
          ))}
        </View>
      ) : null}

      <View style={styles.preview}>
        {days.map((date) => (
          <View key={date} style={styles.dayBlock}>
            <Text style={[styles.dayTitle, { color: colors.ink }]}>{formatShort(date)}</Text>
            <Timeline
              items={tasks.filter((task) => task.dueDate === date).map(toItem)}
              interactive={false}
            />
          </View>
        ))}
      </View>

      <TextField
        label="想改点什么（选填）"
        value={feedback}
        onChangeText={setFeedback}
        placeholder="例如：晚点做 / 少一点 / 挪到周末"
        multiline
        background={colors.surfaceContainerLowest}
      />
      {canAdjust && trimmedFeedback.length === 0 ? (
        <Text style={[styles.hint, { color: colors.inkMuted }]}>
          先写一句想改什么，再点「重新生成」。
        </Text>
      ) : null}

      {warnings.length > 0 ? (
        <View style={styles.warningGroup}>
          <Text style={[styles.groupLabel, { color: colors.inkMuted }]}>补充提示</Text>
          {warnings.map((warning, index) => (
            <Text
              key={`warning-${index}-${warning}`}
              style={[styles.notice, { color: colors.inkMuted }]}>
              · {warning}
            </Text>
          ))}
        </View>
      ) : null}

      {error ? <InlineNotice message={error} onDismiss={onDismissError} /> : null}
      {message ? <Text style={[styles.notice, { color: colors.primary }]}>{message}</Text> : null}

      <Text style={[styles.notice, { color: colors.inkMuted }]}>
        {mode === 'api'
          ? '拆解由后端智能体完成；「重新生成」会把你的反馈交给它重排，确认后才会落库。'
          : '本地模拟预览（mock 模式），用于后端不可用时兜底。'}
      </Text>
      <Text style={[styles.notice, { color: colors.inkMuted }]}>
        确认后会生成正式计划；到了待办页，还可以逐条编辑时间、优先级和完成标准。
      </Text>
    </Dialog>
  );
}

const styles = StyleSheet.create({
  summary: {
    padding: Space.lg,
    gap: Space.xs,
  },
  summaryTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  meta: {
    fontSize: Type.labelLarge,
    lineHeight: Type.labelLarge * Line.normal,
  },
  mono: {
    fontFamily: Fonts.mono,
  },
  alert: {
    borderWidth: 1,
    borderRadius: Radius.sm,
    padding: Space.md,
    gap: Space.xs,
  },
  alertTitle: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
  },
  alertText: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  preview: {
    gap: Space.xl,
  },
  dayBlock: {
    gap: Space.sm,
  },
  dayTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  hint: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
  },
  warningGroup: {
    gap: Space.xs,
  },
  groupLabel: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  notice: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
});
