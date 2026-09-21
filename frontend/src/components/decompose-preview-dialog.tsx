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
  onRegenerate,
  onConfirm,
  onClose,
}: {
  tasks: DraftTask[];
  mode: DataMode;
  onRegenerate: (feedback: string) => void;
  onConfirm: () => Promise<void> | void;
  onClose: () => void;
}) {
  const { colors } = useTheme();
  const [feedback, setFeedback] = useState('');
  const [confirming, setConfirming] = useState(false);

  const days = Array.from(new Set(tasks.map((task) => task.dueDate))).sort();

  async function confirm() {
    setConfirming(true);
    try {
      await onConfirm();
    } finally {
      setConfirming(false);
    }
  }

  return (
    <Dialog
      visible
      width={640}
      title="拆解预览"
      description={`共 ${tasks.length} 条，分布在 ${days.length} 天。预览仅供参考，不可编辑。`}
      onRequestClose={onClose}
      actions={[
        { label: '重新生成', variant: 'tonal', onPress: () => onRegenerate(feedback) },
        {
          label: confirming ? '生成中…' : '就先这样',
          variant: 'filled',
          disabled: confirming,
          onPress: confirm,
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
        拆解由后端智能体完成
        {mode === 'api'
          ? '；点「就先这样」后端会按目标重新拆解，结果可能与预览不同。'
          : '，目前后端还没接上，这里是本地模拟预览。'}
      </Text>
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
