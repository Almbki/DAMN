import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';

import { ReminderSwitch } from '@/components/feedback/reminder-switch';
import { Button } from '@/components/ui/button';
import { InlineNotice, SaveStatus, type SaveState } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { TextField } from '@/components/ui/text-field';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import {
  PREFERENCE_BOUNDS,
  clampPreference,
  normalizeClockTime,
} from '@/domain/preferences';
import {
  cancelDailyFeedbackReminder,
  getFeedbackNotificationStatus,
  requestFeedbackNotificationPermission,
  scheduleDailyFeedbackReminder,
} from '@/notifications/feedback-reminder';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

const TIME_RE = /^([01]\d|2[0-3]):([0-5]\d)$/;

type ReminderNotice = {
  tone: 'info' | 'success' | 'error';
  text: string;
};

function sleepHours(start: string, end: string): number | null {
  if (!TIME_RE.test(start) || !TIME_RE.test(end)) return null;
  const [sh, sm] = start.split(':').map(Number);
  const [eh, em] = end.split(':').map(Number);
  const minutes = (eh * 60 + em - (sh * 60 + sm) + 1440) % 1440;
  return Math.round((minutes / 60) * 10) / 10;
}

export default function ProfileDetailsScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { preferences, updatePreferences, actionError, clearActionError } = usePlan();
  const [start, setStart] = useState(preferences.sleepStart);
  const [end, setEnd] = useState(preferences.sleepEnd);
  const [reminderTime, setReminderTime] = useState(preferences.feedbackTime ?? '');
  const [reminderBusy, setReminderBusy] = useState(false);
  const [reminderNotice, setReminderNotice] = useState<ReminderNotice | null>(null);
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const touchedRef = useRef(false);
  const reminderTouchedRef = useRef(false);
  const reminderReconciledRef = useRef(false);
  const prefsRef = useRef(preferences);
  const actionErrorRef = useRef(actionError);
  const pendingSavesRef = useRef(0);
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isWeb = Platform.OS === 'web';

  // Seed the local time fields from the provider until the user edits them.
  useEffect(() => {
    if (touchedRef.current) return;
    setStart(preferences.sleepStart);
    setEnd(preferences.sleepEnd);
  }, [preferences.sleepStart, preferences.sleepEnd]);

  useEffect(() => {
    if (reminderTouchedRef.current) return;
    setReminderTime(preferences.feedbackTime ?? '');
  }, [preferences.feedbackTime]);

  // Reconcile an already-enabled reminder once the preference is available. Do
  // not prompt for permission here: only re-create the schedule when permission
  // was already granted.
  useEffect(() => {
    if (reminderReconciledRef.current) return;
    if (!preferences.feedbackEnabled) return;
    const time = normalizeClockTime(preferences.feedbackTime);
    if (!time) return;
    reminderReconciledRef.current = true;
    let cancelled = false;

    void (async () => {
      const status = await getFeedbackNotificationStatus();
      if (cancelled) return;

      if (!status.supported) {
        setReminderNotice({
          tone: 'info',
          text:
            status.reason === 'web'
              ? '网页版不支持系统通知；到点后仍会在应用内提醒你写反馈。'
              : '当前设备不支持本地通知；应用内提醒仍会生效。',
        });
        return;
      }

      if (status.permission === 'granted') {
        if (status.scheduled) {
          setReminderNotice({ tone: 'success', text: `每日 ${time} 的反馈提醒已开启。` });
          return;
        }
        const scheduled = await scheduleDailyFeedbackReminder(time);
        if (!cancelled) {
          setReminderNotice({
            tone: scheduled.ok ? 'success' : 'error',
            text: scheduled.message,
          });
        }
        return;
      }

      if (status.permission === 'denied') {
        setReminderNotice({
          tone: 'error',
          text: '系统通知权限未开启；应用内提醒仍会生效。',
        });
        return;
      }

      setReminderNotice({
        tone: 'info',
        text: '系统通知权限还没授予；应用内提醒已生效。',
      });
    })();

    return () => {
      cancelled = true;
    };
  }, [preferences.feedbackEnabled, preferences.feedbackTime]);

  useEffect(() => {
    if (saveState === 'saving') return;
    prefsRef.current = preferences;
  }, [preferences, saveState]);

  useEffect(() => {
    actionErrorRef.current = actionError;
  }, [actionError]);

  useEffect(
    () => () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    },
    [],
  );

  const runSave = async (run: () => Promise<void>) => {
    pendingSavesRef.current += 1;
    setSaveState('saving');
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current);
      idleTimerRef.current = null;
    }
    try {
      await run();
      await new Promise((resolve) => setTimeout(resolve, 40));
      if (actionErrorRef.current) {
        setSaveState('error');
      } else if (pendingSavesRef.current === 1) {
        setSaveState('saved');
        idleTimerRef.current = setTimeout(() => setSaveState('idle'), 2200);
      }
    } catch {
      setSaveState('error');
    } finally {
      pendingSavesRef.current -= 1;
    }
  };

  const hours = sleepHours(start, end);
  const step = PREFERENCE_BOUNDS.availableMinutesPerDay.step;

  function commitSleep(nextStart: string, nextEnd: string) {
    touchedRef.current = true;
    setStart(nextStart);
    setEnd(nextEnd);
    if (TIME_RE.test(nextStart) && TIME_RE.test(nextEnd)) {
      void runSave(() => updatePreferences({ sleepStart: nextStart, sleepEnd: nextEnd }));
    }
  }

  function shiftAvailable(delta: number) {
    const current = prefsRef.current.availableMinutesPerDay;
    const next = clampPreference('availableMinutesPerDay', current + delta);
    if (next === current) return;
    prefsRef.current = { ...prefsRef.current, availableMinutesPerDay: next };
    void runSave(() => updatePreferences({ availableMinutesPerDay: next }));
  }

  function commitReminderTime(value: string) {
    reminderTouchedRef.current = true;
    setReminderTime(value);
    const normalized = normalizeClockTime(value);
    if (!normalized || normalized === preferences.feedbackTime) return;

    if (preferences.feedbackEnabled) {
      setReminderNotice({ tone: 'info', text: `正在改为每天 ${normalized} 提醒…` });
    }

    void runSave(async () => {
      await updatePreferences({ feedbackTime: normalized });
      if (!preferences.feedbackEnabled) return;
      const scheduled = await scheduleDailyFeedbackReminder(normalized);
      setReminderNotice({
        tone: scheduled.ok ? 'success' : scheduled.permission === 'unsupported' ? 'info' : 'error',
        text: scheduled.message,
      });
    });
  }

  function toggleReminder(next: boolean) {
    if (reminderBusy) return;
    reminderReconciledRef.current = true;
    setReminderBusy(true);
    setReminderNotice(null);

    void runSave(async () => {
      if (!next) {
        await updatePreferences({ feedbackEnabled: false });
        const canceled = await cancelDailyFeedbackReminder();
        setReminderNotice({
          tone: 'info',
          text: canceled.ok
            ? '已关闭每日反馈提醒。'
            : '已关闭每日反馈提醒；当前平台没有系统通知可取消。',
        });
        return;
      }

      const typed = normalizeClockTime(reminderTime);
      const stored = normalizeClockTime(preferences.feedbackTime);
      const normalized = typed ?? stored ?? '21:00';
      reminderTouchedRef.current = true;
      setReminderTime(normalized);
      await updatePreferences({ feedbackEnabled: true, feedbackTime: normalized });

      const permission = await requestFeedbackNotificationPermission();
      if (!permission.supported) {
        setReminderNotice({
          tone: 'info',
          text: '当前平台不支持系统通知；到点后仍会在应用内提醒你写反馈。',
        });
        return;
      }
      if (permission.permission !== 'granted') {
        setReminderNotice({
          tone: 'error',
          text: '通知权限没有开启；应用内提醒仍会生效。',
        });
        return;
      }

      const scheduled = await scheduleDailyFeedbackReminder(normalized);
      setReminderNotice({
        tone: scheduled.ok ? 'success' : 'error',
        text: scheduled.message,
      });
    }).finally(() => {
      setReminderBusy(false);
    });
  }

  const normalizedReminderTime = normalizeClockTime(reminderTime);
  const reminderHelper =
    reminderTime.trim().length === 0
      ? '例如 21:00。开启后，到点会在应用里挡住页面，提醒你写反馈。'
      : !normalizedReminderTime
        ? '时间格式用 HH:MM，例如 21:00。'
        : preferences.feedbackEnabled
          ? `每天 ${normalizedReminderTime} 在应用内提醒。`
          : `保存为 ${normalizedReminderTime}，打开开关后生效。`;

  const saveError = saveState === 'error' ? (actionError ?? '保存失败，请稍后重试。') : null;

  return (
    <View style={styles.page}>
      <View style={styles.statusRow}>
        <Text style={[styles.statusText, { color: colors.inkMuted }]}>
          这里的更改会自动保存；作息和每日可投入时间只由这份基础档案负责。
        </Text>
        <SaveStatus state={saveState} />
      </View>

      {saveError || actionError ? (
        <InlineNotice
          message={saveError ?? actionError ?? ''}
          onDismiss={() => {
            clearActionError();
            setSaveState('idle');
          }}
        />
      ) : null}

      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <Text style={[styles.title, { color: colors.ink }]}>作息</Text>
          <Text style={[styles.body, { color: colors.inkMuted }]}>
            用来避免把任务排到你睡觉的时间。改一次会一直生效。
          </Text>
          <View style={styles.times}>
            <View style={styles.timeField}>
              <TextField
                label="入睡"
                value={start}
                onChangeText={(value) => commitSleep(value, end)}
                placeholder="23:30"
                testID="sleep-start"
                background={colors.surfaceContainerLowest}
              />
            </View>
            <View style={styles.timeField}>
              <TextField
                label="起床"
                value={end}
                onChangeText={(value) => commitSleep(start, value)}
                placeholder="07:30"
                testID="sleep-end"
                background={colors.surfaceContainerLowest}
              />
            </View>
          </View>
          <Text style={[styles.helper, { color: colors.inkMuted }]}>
            {hours == null
              ? '时间格式用 HH:MM，例如 23:30。'
              : `大约 ${hours} 小时睡眠。`}
          </Text>
        </View>
      </Surface>

      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <View style={styles.reminderHead}>
            <View style={styles.reminderCopy}>
              <Text style={[styles.title, { color: colors.ink }]}>反馈提醒</Text>
              <Text style={[styles.body, { color: colors.inkMuted }]}>
                到点后提醒你写今天的反馈。
                {isWeb
                  ? '网页版没有系统通知，但应用内提醒照样生效。'
                  : '应用内提醒一定生效，系统通知取决于权限。'}
              </Text>
            </View>
            <ReminderSwitch
              value={preferences.feedbackEnabled}
              onValueChange={toggleReminder}
              label="每日反馈提醒"
              disabled={reminderBusy}
            />
          </View>

          <View style={styles.timeField}>
            <TextField
              label="提醒时间"
              value={reminderTime}
              onChangeText={commitReminderTime}
              placeholder="21:00"
              testID="feedback-time"
              background={colors.surfaceContainerLowest}
            />
          </View>

          <Text style={[styles.helper, { color: colors.inkMuted }]}>{reminderHelper}</Text>

          {reminderNotice ? (
            <InlineNotice
              tone={reminderNotice.tone}
              message={reminderNotice.text}
              onDismiss={() => setReminderNotice(null)}
            />
          ) : null}
        </View>
      </Surface>

      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <Text style={[styles.title, { color: colors.ink }]}>每日可投入时间</Text>
          <Text style={[styles.body, { color: colors.inkMuted }]}>
            你每天愿意拿来执行计划的总时长上限。
          </Text>
          <View style={styles.stepperRow}>
            <Button label="−" variant="outlined" size="sm" onPress={() => shiftAvailable(-step)} />
            <Text style={[styles.value, { color: colors.ink }]}>
              {preferences.availableMinutesPerDay}
              <Text style={[styles.valueUnit, { color: colors.inkMuted }]}> 分钟</Text>
            </Text>
            <Button label="＋" variant="outlined" size="sm" onPress={() => shiftAvailable(step)} />
          </View>
        </View>
      </Surface>

      <Surface level="level0" radius="lg" bordered>
        <View style={styles.crossLink}>
          <Text style={[styles.helper, { color: colors.inkMuted }]}>
            单日上限、任务间缓冲和高认知任务数属于排程策略，在「设置」里调整。
          </Text>
          <Button
            label="去设置排程上限"
            variant="tonal"
            size="sm"
            icon="arrowRight"
            onPress={() => router.push('/settings')}
          />
        </View>
      </Surface>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: Space.xxl,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  statusText: {
    flexGrow: 1,
    flexBasis: 260,
    fontSize: Type.labelLarge,
    lineHeight: Type.labelLarge * Line.normal,
  },
  card: {
    padding: Space.xl,
    gap: Space.md,
  },
  title: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 560,
  },
  reminderHead: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  reminderCopy: {
    flexGrow: 1,
    flexBasis: 240,
    gap: Space.xs,
  },
  times: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  timeField: {
    flexGrow: 1,
    flexBasis: 160,
    maxWidth: 220,
  },
  helper: {
    fontSize: Type.labelMedium,
  },
  stepperRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.lg,
  },
  value: {
    fontFamily: Fonts.mono,
    fontSize: Type.titleLarge,
  },
  valueUnit: {
    fontSize: Type.labelLarge,
  },
  crossLink: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.md,
    padding: Space.lg,
  },
});
