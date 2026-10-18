import { Platform } from 'react-native';

import { normalizeClockTime } from '@/domain/preferences';

/**
 * Daily feedback reminder built on `expo-notifications`.
 *
 * Notifications are native-only: every entry point short-circuits on web with
 * `supported: false` so the UI can show an "unsupported" state instead of
 * crashing. The module is imported dynamically inside the native-only paths so
 * the web bundle never touches the native module.
 */

/** Marker stored in `content.data.kind` so our reminders can be found/cancelled. */
export const DAILY_FEEDBACK_KIND = 'daily-feedback';

export type FeedbackNotificationPermission =
  | 'granted'
  | 'denied'
  | 'undetermined'
  | 'unsupported';

export type FeedbackNotificationUnsupportedReason = 'web' | 'unavailable';

export type FeedbackNotificationStatus =
  | { supported: false; reason: FeedbackNotificationUnsupportedReason }
  | {
      supported: true;
      permission: Exclude<FeedbackNotificationPermission, 'unsupported'>;
      /** True when at least one `daily-feedback` reminder is scheduled. */
      scheduled: boolean;
    };

export type FeedbackPermissionResult = {
  supported: boolean;
  permission: FeedbackNotificationPermission;
  reason: FeedbackNotificationUnsupportedReason | null;
};

export type FeedbackReminderResult = {
  ok: boolean;
  permission: FeedbackNotificationPermission;
  message: string;
};

export type FeedbackReminderCancelResult = {
  ok: boolean;
  canceled: number;
  message: string;
};

type NotificationsModule = typeof import('expo-notifications');
type PermissionStatus = Awaited<
  ReturnType<NotificationsModule['getPermissionsAsync']>
>;

let loadedModule: NotificationsModule | null = null;
let handlerConfigured = false;

async function loadNotifications(): Promise<NotificationsModule | null> {
  if (Platform.OS === 'web') return null;
  if (loadedModule) return loadedModule;
  loadedModule = await import('expo-notifications');
  return loadedModule;
}

/** Foreground presentation so a reminder still appears while the app is open. */
function configureNotificationHandler(Notifications: NotificationsModule): void {
  if (handlerConfigured) return;
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
  handlerConfigured = true;
}

function permissionFrom(status: PermissionStatus): Exclude<
  FeedbackNotificationPermission,
  'unsupported'
> {
  if (status.granted) return 'granted';
  // Provisional / ephemeral iOS authorisation still delivers notifications.
  const iosStatus = status.ios?.status;
  if (
    iosStatus === 3 || // IosAuthorizationStatus.PROVISIONAL
    iosStatus === 4 // IosAuthorizationStatus.EPHEMERAL
  ) {
    return 'granted';
  }
  return status.canAskAgain ? 'undetermined' : 'denied';
}

function webUnsupported(): FeedbackPermissionResult {
  return { supported: false, permission: 'unsupported', reason: 'web' };
}

/**
 * Ask for notification permission (no-op if already granted). On web this
 * resolves to `{ supported: false, permission: 'unsupported', reason: 'web' }`.
 */
export async function requestFeedbackNotificationPermission(): Promise<FeedbackPermissionResult> {
  if (Platform.OS === 'web') return webUnsupported();

  let Notifications: NotificationsModule | null;
  try {
    Notifications = await loadNotifications();
  } catch {
    return { supported: false, permission: 'unsupported', reason: 'unavailable' };
  }
  if (!Notifications) return webUnsupported();

  try {
    const current = await Notifications.getPermissionsAsync();
    if (permissionFrom(current) === 'granted') {
      return { supported: true, permission: 'granted', reason: null };
    }
    if (!current.canAskAgain) {
      return { supported: true, permission: permissionFrom(current), reason: null };
    }
    const next = await Notifications.requestPermissionsAsync({
      ios: { allowAlert: true, allowBadge: false, allowSound: true },
    });
    return { supported: true, permission: permissionFrom(next), reason: null };
  } catch {
    return { supported: true, permission: 'denied', reason: null };
  }
}

/**
 * Replace any existing daily reminder with one that fires every day at `time`
 * (`HH:MM`). Requests permission first; returns a UI-friendly result.
 */
export async function scheduleDailyFeedbackReminder(
  time: string,
): Promise<FeedbackReminderResult> {
  if (Platform.OS === 'web') {
    return { ok: false, permission: 'unsupported', message: '网页版暂不支持每日提醒。' };
  }

  const normalized = normalizeClockTime(time);
  if (!normalized) {
    return { ok: false, permission: 'undetermined', message: '提醒时间格式应为 HH:MM。' };
  }

  let Notifications: NotificationsModule | null;
  try {
    Notifications = await loadNotifications();
  } catch {
    return {
      ok: false,
      permission: 'unsupported',
      message: '当前设备不支持本地通知。',
    };
  }
  if (!Notifications) {
    return { ok: false, permission: 'unsupported', message: '网页版暂不支持每日提醒。' };
  }

  configureNotificationHandler(Notifications);

  const requested = await requestFeedbackNotificationPermission();
  if (requested.permission !== 'granted') {
    return {
      ok: false,
      permission: requested.permission,
      message:
        requested.permission === 'denied'
          ? '通知权限已被拒绝，请在系统设置中开启。'
          : '需要通知权限才能开启每日反馈提醒。',
    };
  }

  const [hour, minute] = normalized.split(':').map(Number);

  try {
    // Replace instead of stacking: only one daily reminder should ever exist.
    await cancelDailyFeedbackReminder();
    await Notifications.scheduleNotificationAsync({
      content: {
        title: '今天的反馈还没记',
        body: '花一分钟记录完成情况，让计划更贴合你的状态。',
        data: { kind: DAILY_FEEDBACK_KIND },
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DAILY,
        hour,
        minute,
      },
    });
    return {
      ok: true,
      permission: 'granted',
      message: `已设置每天 ${normalized} 的反馈提醒。`,
    };
  } catch {
    return { ok: false, permission: 'granted', message: '设置提醒失败，请稍后再试。' };
  }
}

/** Cancel every scheduled notification carrying the `daily-feedback` marker. */
export async function cancelDailyFeedbackReminder(): Promise<FeedbackReminderCancelResult> {
  if (Platform.OS === 'web') {
    return { ok: false, canceled: 0, message: '网页版暂不支持每日提醒。' };
  }

  let Notifications: NotificationsModule | null;
  try {
    Notifications = await loadNotifications();
  } catch {
    return { ok: false, canceled: 0, message: '当前设备不支持本地通知。' };
  }
  if (!Notifications) {
    return { ok: false, canceled: 0, message: '网页版暂不支持每日提醒。' };
  }

  try {
    const scheduled = await Notifications.getAllScheduledNotificationsAsync();
    const matches = scheduled.filter(
      (request) => request.content.data?.kind === DAILY_FEEDBACK_KIND,
    );
    await Promise.all(
      matches.map((request) =>
        Notifications.cancelScheduledNotificationAsync(request.identifier),
      ),
    );
    return {
      ok: true,
      canceled: matches.length,
      message: matches.length > 0 ? '已关闭每日反馈提醒。' : '当前没有开启每日反馈提醒。',
    };
  } catch {
    return { ok: false, canceled: 0, message: '关闭提醒失败，请稍后再试。' };
  }
}

/**
 * Current permission + whether a daily reminder is scheduled. Safe to call from
 * the UI on mount; on web it resolves to `{ supported: false, reason: 'web' }`.
 */
export async function getFeedbackNotificationStatus(): Promise<FeedbackNotificationStatus> {
  if (Platform.OS === 'web') return { supported: false, reason: 'web' };

  let Notifications: NotificationsModule | null;
  try {
    Notifications = await loadNotifications();
  } catch {
    return { supported: false, reason: 'unavailable' };
  }
  if (!Notifications) return { supported: false, reason: 'web' };

  configureNotificationHandler(Notifications);

  try {
    const [permission, scheduled] = await Promise.all([
      Notifications.getPermissionsAsync(),
      Notifications.getAllScheduledNotificationsAsync(),
    ]);
    return {
      supported: true,
      permission: permissionFrom(permission),
      scheduled: scheduled.some(
        (request) => request.content.data?.kind === DAILY_FEEDBACK_KIND,
      ),
    };
  } catch {
    return { supported: true, permission: 'denied', scheduled: false };
  }
}
