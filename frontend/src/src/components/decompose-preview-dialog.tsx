import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Timeline, type TimelineItem } from '@/components/timeline';
import { Dialog } from '@/components/ui/dialog';
import { TextField } from '@/components/ui/text-field';
import { Line, Space, Type } from '@/constants/tokens';
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
 * 可「重新生成」或「就先这样」。真正的拆解由后端智能体完成，当前为本地模拟。
 */
export function DecomposePreviewDialog({
  tasks,
  mode,
  canAdjust,
  busy,
  message,
  stage,
  warnings,
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
  warnings: string[];
  onRegenerate: (feedback: string) => void;
  onConfirm: () => Promise<void> | void;
  onClose: () => void;
}) {
  const { colors } = useTheme();
  const [feedback, setFeedback] = useState('');

  const days = Array.from(new Set(tasks.map((task) => task.dueDate))).sort();

  return (
    <Dialog
      visible
      width={640}
      title="拆解预览"
      description={`共 ${tasks.length} 条，分布在 ${days.length} 天。预览仅供参考，不可编辑。`}
      onRequestClose={onClose}
      actions={[
        {
          label: canAdjust ? '重新生成' : '不能再调整',
          variant: 'tonal',
          disabled: busy || !canAdjust,
          onPress: () => onRegenerate(feedback),
        },
        {
          label: busy ? '处理中…' : '就先这样',
          variant: 'filled',
          disabled: busy,
          onPress: onConfirm,
        },
      ]}>
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

      <Text style={[styles.notice, { color: colors.inkMuted }]}>
        {mode === 'api'
          ? '拆解由后端智能体完成；「重新生成」会把你的反馈交给它重排，确认后才会落库。'
          : '本地模拟预览（mock 模式），用于后端不可用时兜底。'}
      </Text>
      {busy && stage ? (
        <Text style={[styles.notice, { color: colors.primary }]}>{`拆解中 · ${stage}`}</Text>
      ) : null}
      {message ? <Text style={[styles.notice, { color: colors.primary }]}>{message}</Text> : null}
      {warnings.map((warning) => (
        <Text key={warning} style={[styles.notice, { color: colors.inkMuted }]}>
          {warning}
        </Text>
      ))}
    </Dialog>
  );
}

const styles = StyleSheet.create({
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
  notice: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
});
