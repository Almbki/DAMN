import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Banner } from '@/components/task/banner';
import { LevelStepper } from '@/components/task/level-stepper';
import { BottomSheet } from '@/components/ui/bottom-sheet';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Surface } from '@/components/ui/surface';
import { TextField } from '@/components/ui/text-field';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { todayISO } from '@/domain/date';
import { usePlan } from '@/state/plan';
import type { FeedbackResult } from '@/state/plan-context';
import { useTheme } from '@/state/theme';

/** Daily feedback at the bottom of 待办. Completion rate < 50% can trigger a replan. */
export function DailyFeedbackSheet({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  const { colors } = useTheme();
  const {
    stats,
    submitFeedback,
    feedbackHistory,
    refreshFeedbackHistory,
    assessment,
    setAssessment,
    actionError,
    clearActionError,
  } = usePlan();

  const [summary, setSummary] = useState('');
  const [reason, setReason] = useState('');
  const [plan, setPlan] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<FeedbackResult | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [submitStored, setSubmitStored] = useState(false);

  useEffect(() => {
    if (visible) void refreshFeedbackHistory();
  }, [visible, refreshFeedbackHistory]);

  const today = todayISO();
  const history = [...feedbackHistory]
    .sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id)
    .slice(0, 6);
  const todayFeedback = feedbackHistory.filter((item) => item.date.slice(0, 10) === today);
  const hasFeedbackToday = todayFeedback.length > 0 || submitted;

  function handleClose() {
    setResult(null);
    setSubmitted(false);
    setSubmitStored(false);
    onClose();
  }

  async function handleSubmit() {
    setSubmitting(true);
    setResult(null);
    setSubmitStored(false);
    try {
      const response = await submitFeedback({
        completionRate: stats.todayRate,
        freeText: [summary, plan].filter(Boolean).join(' / '),
        delayReason: reason || undefined,
      });
      setResult(response);
      // A cooldown still means the feedback was stored; an arbitrary error
      // message does not. `submitFeedback` folds both into `cooldownMessage`.
      const stored =
        response.replanTriggered ||
        response.cooldownMessage == null ||
        response.cooldownMessage.startsWith('重排冷却中');
      setSubmitted(stored);
      setSubmitStored(stored);
      await refreshFeedbackHistory();
    } finally {
      setSubmitting(false);
    }
  }

  const noPlan = result?.cooldownMessage === '还没有计划，先生成一个。';
  const resultMessage = result
    ? result.replanTriggered
      ? `已生成新计划${result.replanPlanId != null ? `（#${result.replanPlanId}）` : ''}，任务已切到新版本。`
      : result.cooldownMessage ?? '反馈已记录。完成率低于一半时，系统会给你排一张更轻的计划。'
    : null;
  const resultTitle = result?.replanTriggered
    ? '已生成新计划'
    : noPlan
      ? '还没有计划'
      : '反馈已提交';
  const showResult = result != null && (submitStored || noPlan);

  return (
    <BottomSheet
      visible={visible}
      title="每日反馈"
      subtitle="完成率低于一半时，系统会给你排一张更轻的计划，而不是催你补上。"
      onClose={handleClose}
      footer={
        <>
          <Button label="关闭" variant="text" onPress={handleClose} />
          <Button
            label={submitting ? '提交中…' : hasFeedbackToday ? '再提交一次' : '提交反馈'}
            variant="filled"
            onPress={() => {
              void handleSubmit();
            }}
            disabled={submitting}
          />
        </>
      }>
      {actionError ? (
        <Banner
          tone="error"
          title="操作没有完成"
          body={actionError}
          onDismiss={clearActionError}
        />
      ) : showResult ? (
        <Banner
          tone={result?.replanTriggered ? 'success' : noPlan ? 'error' : 'info'}
          title={resultTitle}
          body={resultMessage ?? undefined}
          onDismiss={() => {
            setResult(null);
            setSubmitStored(false);
          }}
        />
      ) : null}

      <View style={styles.statsBlock}>
        <View style={styles.statsRow}>
          <Stat label="今日完成" value={`${stats.todayDone} / ${stats.todayTotal}`} />
          <Stat label="今日完成率" value={`${Math.round(stats.todayRate * 100)}%`} />
          <Stat label="连续完成" value={`${stats.streak} 天`} />
        </View>
        <Progress value={stats.todayRate} />
        <Text style={[styles.note, { color: colors.inkMuted }]}>
          {stats.todayTotal === 0
            ? '今天还没有排任务；这条反馈仍会记录你的状态。'
            : `完成率按今天已完成 / 今天已排任务计算（${stats.todayDone} / ${stats.todayTotal}）。`}
        </Text>
        {hasFeedbackToday ? (
          <View style={[styles.badge, { backgroundColor: colors.secondaryContainer }]}>
            <Text style={[styles.badgeText, { color: colors.onSecondaryContainer }]}>
              今日已反馈 · 可以再提交一次
            </Text>
          </View>
        ) : null}
      </View>

      <View style={styles.levels}>
        <Text style={[styles.sectionTitle, { color: colors.ink }]}>今天的状态</Text>
        <View style={styles.levelGrid}>
          <LevelStepper
            label="精力"
            value={assessment.energy}
            onChange={(value) => setAssessment({ ...assessment, energy: value })}
            lowHint="没电"
            highHint="很足"
          />
          <LevelStepper
            label="压力"
            value={assessment.stress}
            onChange={(value) => setAssessment({ ...assessment, stress: value })}
            lowHint="放松"
            highHint="紧绷"
          />
        </View>
      </View>

      <View style={[styles.divider, { backgroundColor: colors.line }]} />

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

      <View style={styles.history}>
        <View style={styles.sectionHead}>
          <Text style={[styles.sectionTitle, { color: colors.ink }]}>最近反馈</Text>
          <Text style={[styles.counter, { color: colors.inkMuted }]}>
            {feedbackHistory.length > 0 ? `${feedbackHistory.length} 条` : '暂无'}
          </Text>
        </View>

        {history.length === 0 ? (
          <Surface level="level0" radius="lg" bordered style={{ borderStyle: 'dashed' }}>
            <View style={styles.historyEmpty}>
              <Text style={[styles.historyEmptyTitle, { color: colors.ink }]}>
                还没有反馈记录
              </Text>
              <Text style={[styles.note, { color: colors.inkMuted }]}>
                提交后，日期、完成率、精力和压力会留在这里，方便你回看自己这一周的状态。
              </Text>
            </View>
          </Surface>
        ) : (
          history.map((item) => {
            const levels = [
              item.stress_level != null ? `压力 ${item.stress_level}` : null,
              item.energy_level != null ? `精力 ${item.energy_level}` : null,
            ]
              .filter(Boolean)
              .join(' · ');
            return (
              <View
                key={`${item.id}-${item.date}`}
                style={[styles.historyRow, { borderTopColor: colors.outlineVariant }]}>
                <View style={styles.historyTop}>
                  <Text style={[styles.historyDate, { color: colors.inkMuted }]}>
                    {item.date.slice(0, 10)}
                  </Text>
                  <Text style={[styles.historyRate, { color: colors.ink }]}>
                    {Math.round((item.completion_rate ?? 0) * 100)}%
                  </Text>
                  <Text style={[styles.historyLevels, { color: colors.inkMuted }]}>
                    {levels || '未填状态'}
                  </Text>
                </View>
                {item.free_text ? (
                  <Text style={[styles.historyText, { color: colors.ink }]}>{item.free_text}</Text>
                ) : null}
                {item.delay_reason ? (
                  <Text style={[styles.note, { color: colors.inkMuted }]}>
                    原因：{item.delay_reason}
                  </Text>
                ) : null}
              </View>
            );
          })
        )}
      </View>
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
  statsBlock: {
    gap: Space.md,
  },
  statsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.xl,
  },
  stat: {
    gap: Space.xs,
    minWidth: 80,
  },
  statValue: {
    fontFamily: Fonts.mono,
    fontSize: Type.headlineSmall,
  },
  statLabel: {
    fontSize: Type.labelMedium,
  },
  note: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  badge: {
    alignSelf: 'flex-start',
    borderRadius: Radius.pill,
    paddingHorizontal: Space.md,
    paddingVertical: Space.xs,
  },
  badgeText: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  levels: {
    gap: Space.md,
  },
  levelGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.xl,
  },
  sectionTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  sectionHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  counter: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  divider: {
    height: 1,
  },
  history: {
    gap: Space.sm,
  },
  historyEmpty: {
    padding: Space.lg,
    gap: Space.xs,
  },
  historyEmptyTitle: {
    fontSize: Type.bodyLarge,
    fontWeight: '600',
  },
  historyRow: {
    borderTopWidth: 1,
    paddingVertical: Space.sm,
    gap: Space.xs,
  },
  historyTop: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: Space.md,
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
  historyLevels: {
    flexGrow: 1,
    fontSize: Type.labelMedium,
  },
  historyText: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.normal,
  },
});
