import { useRouter } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import type { EstimateAccuracy } from '@/api/types';
import { TodayEstimateCard } from '@/components/feedback/estimate-accuracy';
import { FeedbackHistory } from '@/components/feedback/feedback-history';
import {
  FeedbackResultBanner,
  feedbackSaved,
} from '@/components/feedback/feedback-result';
import { getLastFeedbackDate, markFeedbackSubmitted } from '@/components/feedback/last-feedback';
import { TaskReasonCard } from '@/components/feedback/task-reason-card';
import { ScaleSlider } from '@/components/task/scale-slider';
import { Banner } from '@/components/task/banner';
import { FilterChip } from '@/components/ui/chip';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { Progress } from '@/components/ui/progress';
import { EmptyState, InlineNotice } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { TextField } from '@/components/ui/text-field';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { parseISO, todayISO } from '@/domain/date';
import type { Task } from '@/domain/task';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { usePlan } from '@/state/plan';
import type { FeedbackResult } from '@/state/plan-context';
import { useProfile } from '@/state/profile';
import { useTheme } from '@/state/theme';

const WEEKDAY = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

/** 三档预估准确性；顺序与按钮一致。 */
const ESTIMATE_OPTIONS = ['估高了', '差不多', '估低了'] as const;
const ESTIMATE_VALUES: readonly EstimateAccuracy[] = ['over', 'ok', 'under'];

type ReasonState = { reason: string; note: string };
type EstimateState = { accuracy: EstimateAccuracy | null; actualMinutes: string };

function taskMeta(task: Task): string {
  const planned = task.estimatedMinutes ?? task.predictedDuration;
  const completedStandards = task.standards.filter((standard) => standard.completed).length;
  return [
    planned != null ? `计划 ${planned} 分` : null,
    task.actualMinutes != null ? `实际 ${task.actualMinutes} 分` : null,
    task.standards.length > 0 ? `标准 ${completedStandards}/${task.standards.length}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

export default function FeedbackScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const profile = useProfile();
  const {
    tasks,
    stats,
    assessment,
    setAssessment,
    submitFeedback,
    feedbackHistory,
    refreshFeedbackHistory,
    refresh,
    actionError,
    clearActionError,
  } = usePlan();

  const today = todayISO();
  const todayTasks = useMemo(() => tasks.filter((task) => task.dueDate === today), [tasks, today]);
  const doneTasks = useMemo(() => todayTasks.filter((task) => task.done), [todayTasks]);
  const unfinished = useMemo(() => todayTasks.filter((task) => !task.done), [todayTasks]);
  const skippedCount = useMemo(
    () => todayTasks.filter((task) => task.skipped).length,
    [todayTasks],
  );
  // 只问「直接点完成、从没点开始」且没有实际分钟的任务：有计时的任务实际用时
  // 已由后端按 started_at → finished_at 自动算好，不必再问。
  const estimateCandidates = useMemo(
    () => doneTasks.filter((task) => !task.startedAt && task.actualMinutes == null),
    [doneTasks],
  );
  const allClosed = useMemo(
    () => todayTasks.length > 0 && todayTasks.every((task) => task.done || task.skipped),
    [todayTasks],
  );

  const [reasonByTask, setReasonByTask] = useState<Record<number, ReasonState>>({});
  const [estimateByTask, setEstimateByTask] = useState<Record<number, EstimateState>>({});
  const [dayReview, setDayReview] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<FeedbackResult | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [justSaved, setJustSaved] = useState(false);
  const scrollRef = useRef<ScrollView>(null);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    void refreshFeedbackHistory();
  }, [refreshFeedbackHistory]);

  // Skipped tasks default to the "今天先不做" reason without needing a tap. The
  // fallback lives in render so new tasks (e.g. after a replan) appear too.
  function reasonFor(task: Task): ReasonState {
    return reasonByTask[task.id] ?? { reason: task.skipped ? 'skipped' : '', note: '' };
  }

  const missingCount = unfinished.filter((task) => !reasonFor(task).reason).length;
  const hasFeedbackToday =
    justSaved ||
    getLastFeedbackDate() === today ||
    feedbackHistory.some((item) => item.date.slice(0, 10) === today);

  function setReason(task: Task, reason: string) {
    setReasonByTask((prev) => {
      const current = prev[task.id] ?? { reason: task.skipped ? 'skipped' : '', note: '' };
      return { ...prev, [task.id]: { ...current, reason } };
    });
  }

  function setNote(task: Task, note: string) {
    setReasonByTask((prev) => {
      const current = prev[task.id] ?? { reason: task.skipped ? 'skipped' : '', note: '' };
      return { ...prev, [task.id]: { ...current, note } };
    });
  }

  function estimateFor(task: Task): EstimateState {
    return estimateByTask[task.id] ?? { accuracy: null, actualMinutes: '' };
  }

  function setEstimate(task: Task, accuracy: EstimateAccuracy) {
    setEstimateByTask((prev) => {
      const current = prev[task.id] ?? { accuracy: null, actualMinutes: '' };
      return { ...prev, [task.id]: { ...current, accuracy } };
    });
  }

  function setEstimateMinutes(task: Task, value: string) {
    // Backend accepts 0..1440 minutes; clamp while typing so a typo cannot 422.
    const digits = value.replace(/[^0-9]/g, '').slice(0, 4);
    const capped = digits ? String(Math.min(1440, Number(digits))) : '';
    setEstimateByTask((prev) => {
      const current = prev[task.id] ?? { accuracy: null, actualMinutes: '' };
      return { ...prev, [task.id]: { ...current, actualMinutes: capped } };
    });
  }

  function revealResult() {
    setTimeout(
      () => scrollRef.current?.scrollTo({ y: 0, animated: !reducedMotion }),
      60,
    );
  }

  async function handleSubmit() {
    if (submitting || missingCount > 0) return;
    setSubmitting(true);
    setSubmitError(null);
    setResult(null);
    clearActionError();

    try {
      // 只提交用户真正选了三档的任务；分钟留空表示「没量过」。
      const taskEstimates = estimateCandidates.flatMap((task) => {
        const estimate = estimateFor(task);
        if (!estimate.accuracy) return [];
        const minutes = Number.parseInt(estimate.actualMinutes, 10);
        return [
          {
            taskId: task.id,
            accuracy: estimate.accuracy,
            actualMinutes: Number.isFinite(minutes) && minutes > 0 ? minutes : null,
          },
        ];
      });
      const response = await submitFeedback({
        // Today's rate is automatic: done / (done + open). Skipped work is not
        // counted, matching the plan stats.
        completionRate: stats.todayRate,
        taskReasons: unfinished.map((task) => {
          const state = reasonFor(task);
          return {
            taskId: task.id,
            reason: state.reason,
            note: state.note.trim() || null,
          };
        }),
        dayReview: dayReview.trim().slice(0, 5000) || undefined,
        taskEstimates: taskEstimates.length > 0 ? taskEstimates : undefined,
        closeDay: allClosed,
      });
      setResult(response);
      revealResult();
      if (feedbackSaved(response)) {
        markFeedbackSubmitted(today);
        setJustSaved(true);
        // The backend updates Level 2 during the feedback request. Refresh the
        // profile + plan so the state cards and trend reflect the new observation.
        profile.refresh();
        refresh();
      }
    } catch {
      setSubmitError('反馈提交失败，请稍后再试。');
      revealResult();
    } finally {
      setSubmitting(false);
    }
  }

  if (tasks.length === 0) {
    return (
      <View style={styles.emptyPage}>
        <EmptyState
          title="先生成计划后再写反馈"
          body="反馈会对照今天的计划计算完成率，也会影响下一版怎么排。先去目标页写一个目标。"
          actionLabel="去目标页"
          actionIcon="target"
          onAction={() => router.push('/goal')}
        />
      </View>
    );
  }

  const date = parseISO(today);
  const dateLabel = `${date.getMonth() + 1} 月 ${date.getDate()} 日 · ${WEEKDAY[date.getDay()]}`;
  const hasTasksToday = todayTasks.length > 0;

  return (
    <KeyboardAvoidingView
      style={styles.page}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView
        ref={scrollRef}
        style={styles.scroll}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag">
        <View style={styles.intro}>
          <Text style={[styles.eyebrow, { color: colors.primary }]}>DAILY REVIEW</Text>
          <Text style={[styles.introTitle, { color: colors.ink }]}>把今天收个尾</Text>
          <Text style={[styles.introBody, { color: colors.inkMuted }]}>
            {dateLabel}。完成率自动计算，你只需要给没做完的事选个原因。
          </Text>
        </View>

        {result ? (
          <View style={styles.resultBlock}>
            <FeedbackResultBanner
              result={result}
              onDismiss={() => setResult(null)}
              onGoTodo={() => router.push('/')}
            />
            {feedbackSaved(result) ? <TodayEstimateCard /> : null}
          </View>
        ) : submitError ? (
          <Banner
            tone="error"
            title="反馈提交失败"
            body={submitError}
            onDismiss={() => setSubmitError(null)}
          />
        ) : actionError ? (
          <Banner
            tone="error"
            title="操作没有完成"
            body={actionError}
            onDismiss={clearActionError}
          />
        ) : null}

        <Surface level="level1" radius="lg">
          <View style={styles.statsCard}>
            <View style={styles.statsTop}>
              <View style={styles.rateBlock}>
                <Text style={[styles.cardLabel, { color: colors.inkMuted }]}>自动完成率</Text>
                <Text style={[styles.rateValue, { color: colors.ink }]}>
                  {Math.round(stats.todayRate * 100)}
                  <Text style={[styles.rateUnit, { color: colors.inkFaint }]}>%</Text>
                </Text>
              </View>
              <View style={styles.doneBlock}>
                <Text style={[styles.doneValue, { color: colors.ink }]}>
                  {stats.todayDone} / {stats.todayTotal}
                </Text>
                <Text style={[styles.doneLabel, { color: colors.inkMuted }]}>今日完成</Text>
              </View>
            </View>

            <Progress value={stats.todayRate} />

            <View style={styles.statsFoot}>
              <Text style={[styles.helper, { color: colors.inkMuted }]}>
                {stats.todayTotal === 0
                  ? '今天还没有排任务，完成率会记为 0%。'
                  : `按今天已完成 / 已排任务自动计算${skippedCount > 0 ? `，跳过的 ${skippedCount} 件不计入` : ''}。`}
              </Text>
              {hasFeedbackToday ? (
                <View style={[styles.savedBadge, { backgroundColor: colors.primaryContainer }]}>
                  <Text style={[styles.savedBadgeText, { color: colors.onPrimaryContainer }]}>
                    今日已提交
                  </Text>
                </View>
              ) : null}
            </View>
          </View>
        </Surface>

        <Surface level="level1" radius="lg">
          <View style={styles.card}>
            <View style={styles.cardHead}>
              <Text style={[styles.cardTitle, { color: colors.ink }]}>今天的状态</Text>
              <Text style={[styles.helper, { color: colors.inkFaint }]}>
                会一起影响要不要重排
              </Text>
            </View>
            <View style={styles.sliderRow}>
              <ScaleSlider
                label="精力"
                value={assessment.energy}
                onChange={(value) => setAssessment({ ...assessment, energy: value })}
                lowHint="没电"
                highHint="很足"
              />
              <ScaleSlider
                label="压力"
                value={assessment.stress}
                onChange={(value) => setAssessment({ ...assessment, stress: value })}
                lowHint="放松"
                highHint="紧绷"
              />
            </View>
          </View>
        </Surface>

        {!hasTasksToday ? (
          <InlineNotice
            tone="info"
            message="今天没有排任务。完成率会显示为 0 / 0，但你仍然可以记录精力和压力，这份反馈会保存下来。"
          />
        ) : null}

        {hasTasksToday ? (
          <View style={styles.section}>
            <View style={styles.sectionHead}>
              <Text style={[styles.sectionTitle, { color: colors.ink }]}>
                已完成 · {doneTasks.length}
              </Text>
              <Text style={[styles.sectionHint, { color: colors.inkFaint }]}>自动列出</Text>
            </View>

            {doneTasks.length === 0 ? (
              <Text style={[styles.quiet, { color: colors.inkFaint }]}>
                今天还没有完成的任务。
              </Text>
            ) : (
              doneTasks.map((task) => {
                const meta = taskMeta(task);
                return (
                  <Surface key={task.id} level="level0" radius="lg" bordered>
                    <View style={styles.completedRow}>
                      <View
                        style={[styles.checkBadge, { backgroundColor: colors.primaryContainer }]}>
                        <Icon
                          name="check"
                          size={14}
                          color={colors.onPrimaryContainer}
                          strokeWidth={2.4}
                        />
                      </View>
                      <View style={styles.completedCopy}>
                        <Text style={[styles.taskTitle, { color: colors.ink }]}>{task.title}</Text>
                        {meta ? (
                          <Text style={[styles.taskMeta, { color: colors.inkMuted }]}>{meta}</Text>
                        ) : null}
                      </View>
                    </View>
                  </Surface>
                );
              })
            )}
          </View>
        ) : null}

        {estimateCandidates.length > 0 ? (
          <Surface level="level0" radius="lg" bordered>
            <View style={styles.card}>
              <View style={styles.cardHead}>
                <Text style={[styles.cardTitle, { color: colors.ink }]}>今天估得准吗？</Text>
                <Text style={[styles.helper, { color: colors.inkFaint }]}>这些任务没有计时</Text>
              </View>
              <Text style={[styles.helper, { color: colors.inkMuted }]}>
                它们是直接点完成、没有点开始的。选一下和计划比估得怎么样，帮系统校准以后的估时；实际分钟可选填。
              </Text>
              {estimateCandidates.map((task) => {
                const estimate = estimateFor(task);
                const meta = taskMeta(task);
                return (
                  <View
                    key={task.id}
                    style={[styles.estimateRow, { borderTopColor: colors.outlineVariant }]}>
                    <Text style={[styles.taskTitle, { color: colors.ink }]}>{task.title}</Text>
                    {meta ? (
                      <Text style={[styles.taskMeta, { color: colors.inkMuted }]}>{meta}</Text>
                    ) : null}
                    <View style={styles.estimateChips}>
                      {ESTIMATE_OPTIONS.map((option, index) => (
                        <FilterChip
                          key={option}
                          label={option}
                          selected={estimate.accuracy === ESTIMATE_VALUES[index]}
                          onPress={() => setEstimate(task, ESTIMATE_VALUES[index])}
                        />
                      ))}
                    </View>
                    {estimate.accuracy ? (
                      <TextField
                        label="实际用了多少分钟（可选）"
                        value={estimate.actualMinutes}
                        onChangeText={(value) => setEstimateMinutes(task, value)}
                        placeholder="例如 40"
                        keyboardType="number-pad"
                        background={colors.surfaceContainerLowest}
                      />
                    ) : null}
                  </View>
                );
              })}
            </View>
          </Surface>
        ) : null}

        {allClosed ? (
          <InlineNotice
            tone="success"
            message="今天的任务都处理完了。提交后今天到此结束，应用内不会再提醒你写反馈。"
          />
        ) : null}

        {hasTasksToday ? (
          <View style={styles.section}>
            <View style={styles.sectionHead}>
              <Text style={[styles.sectionTitle, { color: colors.ink }]}>
                没做完 · {unfinished.length}
              </Text>
              <Text style={[styles.sectionHint, { color: colors.inkFaint }]}>
                每件都要选原因
              </Text>
            </View>

            {unfinished.length === 0 ? (
              <Text style={[styles.quiet, { color: colors.inkFaint }]}>
                今天的任务都完成了。
              </Text>
            ) : (
              unfinished.map((task) => {
                const state = reasonFor(task);
                return (
                  <TaskReasonCard
                    key={task.id}
                    task={task}
                    reason={state.reason}
                    note={state.note}
                    missing={!state.reason}
                    onReasonChange={(reason) => setReason(task, reason)}
                    onNoteChange={(note) => setNote(task, note)}
                  />
                );
              })
            )}
          </View>
        ) : null}

        <Surface level="level0" radius="lg" bordered>
          <View style={styles.card}>
            <View style={styles.cardHead}>
              <Text style={[styles.cardTitle, { color: colors.ink }]}>今天的四段反思</Text>
              <Text style={[styles.helper, { color: colors.inkFaint }]}>可选</Text>
            </View>
            <Text style={[styles.helper, { color: colors.inkMuted }]}>
              按四段写：今天做得怎么样 · 哪里卡住 · 今天状态 · 明天怎么看。写成一段也可以，会保存为今天的反思。
            </Text>
            <TextField
              label="写给自己看（可选）"
              value={dayReview}
              onChangeText={setDayReview}
              placeholder={'今天做得怎么样？\n哪里卡住了？\n今天状态如何？\n明天打算怎么安排？'}
              multiline
              background={colors.surfaceContainerLowest}
            />
          </View>
        </Surface>

        <FeedbackHistory history={feedbackHistory} tasks={tasks} />
      </ScrollView>

      <View
        style={[
          styles.footer,
          { borderTopColor: colors.outlineVariant, backgroundColor: colors.surface },
        ]}>
        <View style={styles.footerCopy}>
          <Text
            accessibilityLiveRegion="polite"
            style={[
              styles.footerHint,
              { color: missingCount > 0 ? colors.error : colors.inkMuted },
            ]}>
            {missingCount > 0
              ? `还有 ${missingCount} 个未完成任务没选原因`
              : unfinished.length > 0
                ? '原因都选好了，可以提交。'
                : allClosed
                  ? '今天到此结束，提交即可。'
                  : '只记录状态也可以提交。'}
          </Text>
          <Text style={[styles.footerMeta, { color: colors.inkFaint }]}>
            自动完成率 {Math.round(stats.todayRate * 100)}%
          </Text>
        </View>
        <Button
          label={submitting ? '提交中…' : '提交反馈'}
          variant="filled"
          disabled={submitting || missingCount > 0}
          onPress={() => {
            void handleSubmit();
          }}
        />
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    minHeight: 0,
  },
  emptyPage: {
    paddingTop: Space.xl,
  },
  scroll: {
    flex: 1,
    minHeight: 0,
  },
  content: {
    gap: Space.xl,
    paddingBottom: Space.xl,
  },
  resultBlock: {
    gap: Space.md,
  },
  intro: {
    gap: Space.xs,
  },
  eyebrow: {
    fontFamily: Fonts.mono,
    fontSize: Type.labelMedium,
    letterSpacing: 1.6,
  },
  introTitle: {
    fontSize: Type.headlineSmall,
    lineHeight: Type.headlineSmall * Line.tight,
    fontWeight: '600',
  },
  introBody: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 560,
  },
  statsCard: {
    padding: Space.xl,
    gap: Space.md,
  },
  statsTop: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.lg,
  },
  rateBlock: {
    gap: Space.xs,
  },
  cardLabel: {
    fontSize: Type.labelMedium,
  },
  rateValue: {
    fontFamily: Fonts.mono,
    fontSize: Type.displaySmall,
    lineHeight: Type.displaySmall * Line.tight,
  },
  rateUnit: {
    fontSize: Type.titleLarge,
  },
  doneBlock: {
    alignItems: 'flex-end',
    gap: 2,
  },
  doneValue: {
    fontFamily: Fonts.mono,
    fontSize: Type.titleLarge,
  },
  doneLabel: {
    fontSize: Type.labelMedium,
  },
  statsFoot: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  helper: {
    flexGrow: 1,
    flexBasis: 240,
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  savedBadge: {
    borderRadius: Radius.pill,
    paddingHorizontal: Space.md,
    paddingVertical: Space.xs,
  },
  savedBadgeText: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
  card: {
    padding: Space.xl,
    gap: Space.lg,
  },
  cardHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  cardTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  sliderRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.xl,
  },
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
  sectionHint: {
    fontSize: Type.labelMedium,
  },
  quiet: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    paddingVertical: Space.sm,
  },
  estimateRow: {
    gap: Space.sm,
    borderTopWidth: 1,
    paddingTop: Space.md,
  },
  estimateChips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  completedRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Space.md,
    padding: Space.lg,
  },
  checkBadge: {
    width: 26,
    height: 26,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
  },
  completedCopy: {
    flex: 1,
    minWidth: 0,
    gap: 2,
  },
  taskTitle: {
    fontSize: Type.bodyLarge,
    lineHeight: Type.bodyLarge * Line.normal,
    fontWeight: '600',
  },
  taskMeta: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.md,
    borderTopWidth: 1,
    paddingTop: Space.md,
    paddingBottom: Space.xs,
  },
  footerCopy: {
    flexGrow: 1,
    flexBasis: 220,
    gap: 2,
  },
  footerHint: {
    fontSize: Type.labelLarge,
    lineHeight: Type.labelLarge * Line.normal,
    fontWeight: '600',
  },
  footerMeta: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
});
