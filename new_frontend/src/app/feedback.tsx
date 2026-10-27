import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { FeedbackHistory } from '@/components/feedback/feedback-history';
import {
  FeedbackResultBanner,
  feedbackSaved,
} from '@/components/feedback/feedback-result';
import { getLastFeedbackDate, markFeedbackSubmitted } from '@/components/feedback/last-feedback';
import { TaskReasonCard } from '@/components/feedback/task-reason-card';
import { ScaleSlider } from '@/components/task/scale-slider';
import { Banner } from '@/components/task/banner';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { Progress } from '@/components/ui/progress';
import { EmptyState, InlineNotice } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { TextField } from '@/components/ui/text-field';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { parseISO, todayISO } from '@/domain/date';
import {
  feedbackObligationForDate,
  retrospectiveObligations,
} from '@/domain/feedback-obligation';
import { isClosed, type Task } from '@/domain/task';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { usePlan } from '@/state/plan';
import type { FeedbackResult } from '@/state/plan-context';
import { useProfile } from '@/state/profile';
import { useTheme } from '@/state/theme';

const WEEKDAY = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

function formatDay(date: string): string {
  const day = parseISO(date);
  return `${day.getMonth() + 1} 月 ${day.getDate()} 日 · ${WEEKDAY[day.getDay()]}`;
}

type ReasonState = { reason: string; note: string };

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

function poolMeta(task: Task, goalTitleById: Map<number, string>): string {
  const planned = task.estimatedMinutes ?? task.predictedDuration;
  const goal = task.goalId != null ? goalTitleById.get(task.goalId) : null;
  return [
    planned != null ? `计划 ${planned} 分` : null,
    goal ?? '未归入目标',
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
    goals,
    backlogTasks,
    assessment,
    setAssessment,
    setDone,
    submitFeedback,
    feedbackHistory,
    refreshFeedbackHistory,
    feedbackObligations,
    refreshFeedbackObligations,
    refresh,
    actionError,
    clearActionError,
  } = usePlan();
  const params = useLocalSearchParams();

  const today = todayISO();
  const rawDate = params.date;
  const paramDate =
    typeof rawDate === 'string' ? rawDate : Array.isArray(rawDate) ? rawDate[0] : undefined;
  const selectedDate =
    paramDate && /^\d{4}-\d{2}-\d{2}$/.test(paramDate) ? paramDate : today;
  const isRetrospective = selectedDate < today;

  const dayTasks = useMemo(
    () => tasks.filter((task) => task.dueDate === selectedDate),
    [tasks, selectedDate],
  );
  const doneTasks = useMemo(() => dayTasks.filter((task) => task.done), [dayTasks]);
  const unfinished = useMemo(() => dayTasks.filter((task) => !task.done), [dayTasks]);
  const skippedCount = useMemo(
    () => dayTasks.filter((task) => task.skipped).length,
    [dayTasks],
  );
  const openCount = useMemo(() => dayTasks.filter((task) => !isClosed(task)).length, [dayTasks]);
  const dayTotal = doneTasks.length + openCount;
  const dayRate = dayTotal === 0 ? 0 : doneTasks.length / dayTotal;

  const obligation = useMemo(
    () => feedbackObligationForDate(feedbackObligations, selectedDate),
    [feedbackObligations, selectedDate],
  );
  const backfill = useMemo(
    () => retrospectiveObligations(feedbackObligations, today),
    [feedbackObligations, today],
  );
  const openBacklog = useMemo(
    () => backlogTasks.filter((task) => !isClosed(task)),
    [backlogTasks],
  );
  const goalTitleById = useMemo(
    () => new Map(goals.map((goal) => [goal.id, goal.title])),
    [goals],
  );

  const [reasonByTask, setReasonByTask] = useState<Record<number, ReasonState>>({});
  const [freeText, setFreeText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<FeedbackResult | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [savedDate, setSavedDate] = useState<string | null>(null);
  const scrollRef = useRef<ScrollView>(null);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    void refreshFeedbackHistory();
    void refreshFeedbackObligations();
  }, [refreshFeedbackHistory, refreshFeedbackObligations]);

  // Skipped tasks default to the "今天先不做" reason without needing a tap. The
  // fallback lives in render so new tasks (e.g. after a replan) appear too.
  function reasonFor(task: Task): ReasonState {
    return reasonByTask[task.id] ?? { reason: task.skipped ? 'skipped' : '', note: '' };
  }

  const missingCount = unfinished.filter((task) => !reasonFor(task).reason).length;
  const hasFeedbackForDate =
    savedDate === selectedDate ||
    getLastFeedbackDate() === selectedDate ||
    feedbackHistory.some((item) => item.date.slice(0, 10) === selectedDate);

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
      const response = await submitFeedback({
        // This day's rate is automatic: done / (done + open). Skipped work is
        // not counted, matching the plan stats.
        completionRate: dayRate,
        date: selectedDate,
        planId: obligation?.plan_id ?? undefined,
        taskReasons: unfinished.map((task) => {
          const state = reasonFor(task);
          return {
            taskId: task.id,
            reason: state.reason,
            note: state.note.trim() || null,
          };
        }),
        freeText: freeText.trim() || undefined,
      });
      setResult(response);
      revealResult();
      if (feedbackSaved(response)) {
        setSavedDate(selectedDate);
        // The local marker only protects today's gate; a backfill is tracked by
        // the backend obligations instead.
        if (selectedDate === today) markFeedbackSubmitted(selectedDate);
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

  const dateLabel = formatDay(selectedDate);
  const hasTasksForDate = dayTasks.length > 0;

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
          <Text style={[styles.introTitle, { color: colors.ink }]}>
            {isRetrospective ? '补一份那天的反馈' : '把今天收个尾'}
          </Text>
          <Text style={[styles.introBody, { color: colors.inkMuted }]}>
            {dateLabel}。完成率按这一天的任务自动计算，你只需要给没做完的事选个原因。
          </Text>
        </View>

        {result ? (
          <FeedbackResultBanner
            result={result}
            onDismiss={() => setResult(null)}
            onGoTodo={() => router.push('/')}
          />
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

        {backfill.length > 0 ? (
          <Surface level="level0" radius="lg" bordered>
            <View style={styles.backfill}>
              <View style={styles.cardHead}>
                <Text style={[styles.cardTitle, { color: colors.ink }]}>待补填</Text>
                <Text style={[styles.helper, { color: colors.inkFaint }]}>
                  {backfill.length} 天没有提交反馈
                </Text>
              </View>
              {backfill.map((item) => (
                <View
                  key={item.execution_date}
                  style={[styles.backfillRow, { borderTopColor: colors.outlineVariant }]}>
                  <Text style={[styles.backfillDate, { color: colors.ink }]}>
                    {formatDay(item.execution_date)}
                  </Text>
                  {selectedDate === item.execution_date ? (
                    <Text style={[styles.helper, { color: colors.inkFaint }]}>正在补填</Text>
                  ) : (
                    <Button
                      label="补填"
                      variant="text"
                      size="sm"
                      onPress={() => router.setParams({ date: item.execution_date })}
                    />
                  )}
                </View>
              ))}
            </View>
          </Surface>
        ) : null}

        {isRetrospective ? (
          <InlineNotice
            tone="info"
            message="这是补填历史日期。补填只记录当天的情况，不会触发重排。"
          />
        ) : null}

        <Surface level="level1" radius="lg">
          <View style={styles.statsCard}>
            <View style={styles.statsTop}>
              <View style={styles.rateBlock}>
                <Text style={[styles.cardLabel, { color: colors.inkMuted }]}>自动完成率</Text>
                <Text style={[styles.rateValue, { color: colors.ink }]}>
                  {Math.round(dayRate * 100)}
                  <Text style={[styles.rateUnit, { color: colors.inkFaint }]}>%</Text>
                </Text>
              </View>
              <View style={styles.doneBlock}>
                <Text style={[styles.doneValue, { color: colors.ink }]}>
                  {doneTasks.length} / {dayTotal}
                </Text>
                <Text style={[styles.doneLabel, { color: colors.inkMuted }]}>
                  {isRetrospective ? '当日完成' : '今日完成'}
                </Text>
              </View>
            </View>

            <Progress value={dayRate} />

            <View style={styles.statsFoot}>
              <Text style={[styles.helper, { color: colors.inkMuted }]}>
                {dayTotal === 0
                  ? isRetrospective
                    ? '这一天没有排任务，完成率会记为 0%。'
                    : '今天还没有排任务，完成率会记为 0%。'
                  : `按${isRetrospective ? '当天' : '今天'}已完成 / 已排任务自动计算${skippedCount > 0 ? `，跳过的 ${skippedCount} 件不计入` : ''}。`}
              </Text>
              {hasFeedbackForDate ? (
                <View style={[styles.savedBadge, { backgroundColor: colors.primaryContainer }]}>
                  <Text style={[styles.savedBadgeText, { color: colors.onPrimaryContainer }]}>
                    {isRetrospective ? '当日已提交' : '今日已提交'}
                  </Text>
                </View>
              ) : null}
            </View>
          </View>
        </Surface>

        <Surface level="level1" radius="lg">
          <View style={styles.card}>
            <View style={styles.cardHead}>
              <Text style={[styles.cardTitle, { color: colors.ink }]}>
                {isRetrospective ? '这一天的状态' : '今天的状态'}
              </Text>
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

        {!hasTasksForDate ? (
          <InlineNotice
            tone="info"
            message={
              isRetrospective
                ? '这一天没有排任务。完成率会显示为 0 / 0，但你仍然可以提交一条补填记录。'
                : '今天没有排任务。完成率会显示为 0 / 0，但你仍然可以记录精力和压力，这份反馈会保存下来。'
            }
          />
        ) : null}

        {hasTasksForDate ? (
          <View style={styles.section}>
            <View style={styles.sectionHead}>
              <Text style={[styles.sectionTitle, { color: colors.ink }]}>
                已完成 · {doneTasks.length}
              </Text>
              <Text style={[styles.sectionHint, { color: colors.inkFaint }]}>自动列出</Text>
            </View>

            {doneTasks.length === 0 ? (
              <Text style={[styles.quiet, { color: colors.inkFaint }]}>
                {isRetrospective ? '这一天没有已完成的任务。' : '今天还没有完成的任务。'}
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

        {hasTasksForDate ? (
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
                {isRetrospective ? '这一天的任务都完成了。' : '今天的任务都完成了。'}
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
                    onComplete={
                      !isClosed(task) ? () => setDone(task.id, true) : undefined
                    }
                  />
                );
              })
            )}
          </View>
        ) : null}

        {selectedDate === today && openBacklog.length > 0 ? (
          <View style={styles.section}>
            <View style={styles.sectionHead}>
              <Text style={[styles.sectionTitle, { color: colors.ink }]}>
                任务池 · {openBacklog.length}
              </Text>
              <Text style={[styles.sectionHint, { color: colors.inkFaint }]}>
                没有排日期，完成会直接记完成
              </Text>
            </View>

            {openBacklog.map((task) => (
              <Surface key={task.id} level="level0" radius="lg" bordered>
                <View style={styles.poolRow}>
                  <View style={styles.poolCopy}>
                    <Text style={[styles.taskTitle, { color: colors.ink }]}>{task.title}</Text>
                    <Text style={[styles.taskMeta, { color: colors.inkMuted }]}>
                      {poolMeta(task, goalTitleById)}
                    </Text>
                  </View>
                  <Button
                    label="已完成"
                    variant="filled"
                    size="sm"
                    icon="check"
                    onPress={() => setDone(task.id, true)}
                  />
                </View>
              </Surface>
            ))}
          </View>
        ) : null}

        <Surface level="level0" radius="lg" bordered>
          <View style={styles.card}>
            <Text style={[styles.cardTitle, { color: colors.ink }]}>想补充的</Text>
            <TextField
              label={isRetrospective ? '这一天还有什么想说的（可选）' : '今天还有什么想说的（可选）'}
              value={freeText}
              onChangeText={setFreeText}
              placeholder={
                isRetrospective
                  ? '比如：那天下午状态突然变差、任务拆分得太粗…'
                  : '比如：下午状态突然变差、任务拆分得太粗…'
              }
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
                : '只记录状态也可以提交。'}
          </Text>
          <Text style={[styles.footerMeta, { color: colors.inkFaint }]}>
            自动完成率 {Math.round(dayRate * 100)}%
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
  backfill: {
    padding: Space.lg,
    gap: Space.sm,
  },
  backfillRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
    borderTopWidth: 1,
    paddingTop: Space.sm,
  },
  backfillDate: {
    flex: 1,
    minWidth: 0,
    fontFamily: Fonts.mono,
    fontSize: Type.labelMedium,
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
  poolRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    padding: Space.lg,
  },
  poolCopy: {
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
