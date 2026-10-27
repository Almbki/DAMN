import { usePathname, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { AppState, StyleSheet, Text, View } from 'react-native';

import { getLastFeedbackDate } from '@/components/feedback/last-feedback';
import { Dialog } from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import { toISO } from '@/domain/date';
import {
  nextFeedbackObligation,
  retrospectiveDebtLabel,
  retrospectiveDayCount,
} from '@/domain/feedback-obligation';
import { normalizeClockTime } from '@/domain/preferences';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

const SNOOZE_MINUTES = 15;
const MAX_SNOOZES = 2;
const CHECK_INTERVAL_MS = 30_000;

function minutesFor(time: string | null): number | null {
  const normalized = normalizeClockTime(time);
  if (!normalized) return null;
  const [hour, minute] = normalized.split(':').map(Number);
  return hour * 60 + minute;
}

type Snooze = { date: string; count: number; until: number };

/**
 * The blocking "today's feedback is due" gate.
 *
 * It only appears when reminders are enabled, a plan has tasks, the local clock
 * has reached the chosen time, and neither the feedback history nor the local
 * last-submission marker says today is already done. It cannot be dismissed by
 * tapping outside; the two escapes are a 15-minute snooze (twice) and going to
 * the feedback screen.
 */
export function FeedbackGate() {
  const { colors } = useTheme();
  const {
    preferences,
    tasks,
    stats,
    feedbackHistory,
    refreshFeedbackHistory,
    feedbackObligations,
    refreshFeedbackObligations,
  } = usePlan();
  const pathname = usePathname();
  const router = useRouter();
  const [now, setNow] = useState(() => Date.now());
  const [snooze, setSnooze] = useState<Snooze>({ date: '', count: 0, until: 0 });
  const snoozeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refreshedRef = useRef(false);

  const today = toISO(new Date(now));
  const nowMinutes = new Date(now).getHours() * 60 + new Date(now).getMinutes();
  const targetMinutes = minutesFor(preferences.feedbackTime);
  const snoozeCount = snooze.date === today ? snooze.count : 0;
  const snoozeUntil = snooze.date === today ? snooze.until : 0;

  const lastSubmitted = getLastFeedbackDate();
  const feedbackToday =
    lastSubmitted === today ||
    feedbackHistory.some((item) => item.date.slice(0, 10) === today);

  // Re-evaluate when the app comes back to the foreground and once in a while
  // while it stays open, so the gate can appear at the chosen minute.
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), CHECK_INTERVAL_MS);
    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') setNow(Date.now());
    });
    return () => {
      clearInterval(interval);
      subscription.remove();
    };
  }, []);

  useEffect(
    () => () => {
      if (snoozeTimerRef.current) clearTimeout(snoozeTimerRef.current);
    },
    [],
  );

  useEffect(() => {
    if (!preferences.feedbackEnabled || refreshedRef.current) return;
    if (tasks.length === 0) return;
    refreshedRef.current = true;
    void refreshFeedbackHistory();
    void refreshFeedbackObligations();
  }, [
    preferences.feedbackEnabled,
    refreshFeedbackHistory,
    refreshFeedbackObligations,
    tasks.length,
  ]);

  const retrospectiveDays = retrospectiveDayCount(feedbackObligations, today);
  const hasRetrospective = retrospectiveDays > 0;
  const todayPending =
    feedbackObligations.some((item) => item.execution_date === today) && !feedbackToday;
  // Today still waits for the chosen reminder time; an existing historical debt
  // surfaces immediately, because it already happened.
  const todayDue =
    todayPending && targetMinutes != null && nowMinutes >= targetMinutes;

  const onFeedbackScreen = pathname.replace(/\/+$/, '') === '/feedback';
  const visible =
    !onFeedbackScreen &&
    preferences.feedbackEnabled &&
    tasks.length > 0 &&
    (hasRetrospective || todayDue) &&
    (snoozeUntil === 0 || now >= snoozeUntil);

  function snoozeForFifteen() {
    if (snoozeCount >= MAX_SNOOZES) return;
    const until = Date.now() + SNOOZE_MINUTES * 60_000;
    setSnooze({ date: today, count: snoozeCount + 1, until });
    setNow(Date.now());
    if (snoozeTimerRef.current) clearTimeout(snoozeTimerRef.current);
    snoozeTimerRef.current = setTimeout(
      () => setNow(Date.now()),
      SNOOZE_MINUTES * 60_000 + 250,
    );
  }

  function goToFeedback() {
    const oldest = nextFeedbackObligation(feedbackObligations);
    if (oldest && oldest.execution_date < today) {
      router.push({ pathname: '/feedback', params: { date: oldest.execution_date } });
      return;
    }
    router.push('/feedback');
  }

  const title = hasRetrospective
    ? todayPending
      ? '还有反馈没补完'
      : '有几天的反馈没补'
    : '今天的反馈还没写';
  const description = hasRetrospective
    ? todayPending
      ? `${retrospectiveDebtLabel(retrospectiveDays)}，今天的也还没有写。`
      : `${retrospectiveDebtLabel(retrospectiveDays)}，补上之后计划会更贴合当时的你。`
    : '花一分钟记下今天的完成情况，计划会更贴合你现在的状态。';

  return (
    <Dialog
      visible={visible}
      title={title}
      description={description}
      closable={false}
      onRequestClose={() => undefined}
      width={440}
      actions={[
        {
          label: '稍后 15 分钟',
          variant: 'text',
          disabled: snoozeCount >= MAX_SNOOZES,
          onPress: snoozeForFifteen,
        },
        {
          label: hasRetrospective ? '去补反馈' : '去写反馈',
          variant: 'filled',
          onPress: goToFeedback,
        },
      ]}>
      <View style={styles.body}>
        {todayDue ? (
          <>
            <View style={styles.progressRow}>
              <Text style={[styles.progressLabel, { color: colors.inkMuted }]}>今日完成</Text>
              <Text style={[styles.progressValue, { color: colors.ink }]}>
                {stats.todayDone} / {stats.todayTotal}
              </Text>
            </View>
            <Progress value={stats.todayRate} />
          </>
        ) : null}
        <Text style={[styles.helper, { color: colors.inkMuted }]}>
          {snoozeCount > 0
            ? `已经稍后 ${snoozeCount} 次${snoozeCount >= MAX_SNOOZES ? '，这次就先写掉吧。' : '，还可以再稍后一次。'}`
            : hasRetrospective
              ? '补填只记录那一天的情况，不会触发重排。'
              : '提醒时间来自「基础档案 → 反馈提醒」。写完反馈后这个窗口会自动消失。'}
        </Text>
      </View>
    </Dialog>
  );
}

const styles = StyleSheet.create({
  body: {
    gap: Space.md,
  },
  progressRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  progressLabel: {
    fontSize: Type.labelMedium,
  },
  progressValue: {
    fontFamily: Fonts.mono,
    fontSize: Type.titleLarge,
  },
  helper: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
});
