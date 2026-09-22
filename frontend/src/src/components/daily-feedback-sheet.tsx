import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { BottomSheet } from '@/components/ui/bottom-sheet';
import { Button } from '@/components/ui/button';
import { TextField } from '@/components/ui/text-field';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import { usePlan } from '@/state/plan';
import type { FeedbackResult } from '@/state/plan-context';
import { useTheme } from '@/state/theme';

/** Daily feedback at the bottom of 待办. Completion rate < 50% can trigger a replan. */
export function DailyFeedbackSheet({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  const { colors } = useTheme();
  const { stats, submitFeedback, feedbackHistory, refreshFeedbackHistory } = usePlan();
  const [summary, setSummary] = useState('');
  const [reason, setReason] = useState('');
  const [plan, setPlan] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<FeedbackResult | null>(null);

  useEffect(() => {
    if (visible) void refreshFeedbackHistory();
  }, [visible, refreshFeedbackHistory]);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const response = await submitFeedback({
        completionRate: stats.rate,
        freeText: [summary, plan].filter(Boolean).join(' / '),
        delayReason: reason || undefined,
      });
      setResult(response);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <BottomSheet
      visible={visible}
      title="每日反馈"
      subtitle="完成率低于一半时，系统会给你排一张更轻的计划，而不是催你补上。"
      onClose={onClose}
      footer={
        <>
          <Button label="关闭" variant="text" onPress={onClose} />
          <Button
            label={submitting ? '提交中…' : result ? '再提交一次' : '提交反馈'}
            variant="filled"
            onPress={handleSubmit}
            disabled={submitting}
          />
        </>
      }>
      <View style={styles.stats}>
        <Stat label="今天完成" value={String(stats.completedToday)} />
        <Stat label="完成率" value={`${Math.round(stats.rate * 100)}%`} />
        <Stat label="连续完成" value={`${stats.streak} 天`} />
      </View>

      <TextField
        label="今天完成了什么"
        value={summary}
        onChangeText={setSummary}
        placeholder="简述今天完成的任务…"
        background={colors.surfaceContainerLowest}
      />
      <TextField
        label="没做完的原因"
        value={reason}
        onChangeText={setReason}
        placeholder="例如：被打断、预估时间不足…"
        background={colors.surfaceContainerLowest}
      />
      <TextField
        label="明天想怎么调整"
        value={plan}
        onChangeText={setPlan}
        placeholder="例如：减少任务量、换个时间段…"
        background={colors.surfaceContainerLowest}
      />

      {result ? (
        <Text style={[styles.result, { color: colors.primary }]}>
          {result.replanTriggered
            ? '已根据这次反馈生成新一版计划，任务已切到新版本。'
            : result.cooldownMessage ?? '已提交。完成率低于一半时会生成新一版计划。'}
        </Text>
      ) : null}

      {feedbackHistory.length > 0 ? (
        <View style={styles.history}>
          <Text style={[styles.historyTitle, { color: colors.ink }]}>历史反馈</Text>
          {feedbackHistory
            .slice(-5)
            .reverse()
            .map((item) => (
              <View
                key={item.id}
                style={[styles.historyRow, { borderTopColor: colors.outlineVariant }]}>
                <Text style={[styles.historyDate, { color: colors.inkMuted }]}>{item.date}</Text>
                <Text style={[styles.historyRate, { color: colors.ink }]}>
                  {Math.round((item.completion_rate ?? 0) * 100)}%
                </Text>
                <Text style={[styles.historyMeta, { color: colors.inkMuted }]}>
                  {item.stress_level != null ? `压力 ${item.stress_level}` : ''}
                  {item.energy_level != null ? ` · 精力 ${item.energy_level}` : ''}
                </Text>
              </View>
            ))}
        </View>
      ) : null}
    </BottomSheet>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.stat}>
      <Text style={[styles.statValue, { color: colors.ink }]}>{value}</Text>
      <Text style={[styles.statLabel, { color: colors.inkMuted }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  stats: {
    flexDirection: 'row',
    gap: Space.xxl,
  },
  stat: {
    gap: Space.xs,
  },
  statValue: {
    fontFamily: Fonts.mono,
    fontSize: Type.headlineSmall,
  },
  statLabel: {
    fontSize: Type.labelMedium,
  },
  result: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
  },
  history: {
    gap: Space.xs,
  },
  historyTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  historyRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: Space.md,
    borderTopWidth: 1,
    paddingVertical: Space.sm,
    flexWrap: 'wrap',
  },
  historyDate: {
    fontFamily: Fonts.mono,
    fontSize: Type.labelMedium,
    minWidth: 88,
  },
  historyRate: {
    fontFamily: Fonts.mono,
    fontSize: Type.bodyLarge,
    minWidth: 48,
  },
  historyMeta: {
    flexGrow: 1,
    fontSize: Type.labelMedium,
  },
});
