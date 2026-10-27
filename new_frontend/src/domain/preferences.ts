import type { SchedulingPreferences as ApiSchedulingPreferences } from '@/api/types';

/**
 * Scheduling preferences the user sets once and expects to keep. The backend
 * currently only reads these from each `POST /plans/generate` body (see
 * docs/design/backend-api-gaps.md §7), so the frontend persists them locally
 * and composes every generate request from them.
 */
export interface SchedulingPreferences {
  availableMinutesPerDay: number;
  dailyLimitMinutes: number;
  bufferMinutes: number;
  highCognitiveMaxPerDay: number;
  /** HARD cap for one goal's total scheduled minutes on one day. */
  maxDailyMinutesPerGoal: number;
  /** Local clock, `HH:MM`. */
  sleepStart: string;
  sleepEnd: string;
  /** Local clock, `HH:MM`; `null` until the user picks a reminder time. */
  feedbackTime: string | null;
  /** Whether the daily feedback reminder is enabled. */
  feedbackEnabled: boolean;
  /** Move past unfinished normal tasks to the 任务池 on reconciliation. */
  autoBacklogOverdue: boolean;
}

export type { ApiSchedulingPreferences };

export const DEFAULT_PREFERENCES: SchedulingPreferences = {
  availableMinutesPerDay: 480,
  dailyLimitMinutes: 300,
  bufferMinutes: 15,
  highCognitiveMaxPerDay: 2,
  maxDailyMinutesPerGoal: 120,
  sleepStart: '23:30',
  sleepEnd: '07:30',
  feedbackTime: null,
  feedbackEnabled: false,
  autoBacklogOverdue: false,
};

export const PREFERENCE_BOUNDS = {
  availableMinutesPerDay: { min: 30, max: 1440, step: 15 },
  dailyLimitMinutes: { min: 30, max: 1440, step: 15 },
  bufferMinutes: { min: 0, max: 120, step: 5 },
  highCognitiveMaxPerDay: { min: 1, max: 10, step: 1 },
} as const;

export function clampPreference(key: keyof typeof PREFERENCE_BOUNDS, value: number): number {
  const { min, max } = PREFERENCE_BOUNDS[key];
  return Math.min(max, Math.max(min, Math.round(value)));
}

/**
 * Normalise an `HH:MM` clock value. Returns `null` for empty or invalid input so
 * the UI can distinguish "never set" from a real reminder time.
 */
export function normalizeClockTime(value: string | null | undefined): string | null {
  if (!value) return null;
  const match = /^(\d{1,2}):(\d{2})$/.exec(value.trim());
  if (!match) return null;
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null;
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
}

/** Coerce cached/server preferences into the domain shape (invalid reminder time → `null`). */
export function normalizePreferences(
  preferences: SchedulingPreferences,
): SchedulingPreferences {
  return {
    ...preferences,
    feedbackTime: normalizeClockTime(preferences.feedbackTime),
    feedbackEnabled: Boolean(preferences.feedbackEnabled),
    autoBacklogOverdue: Boolean(preferences.autoBacklogOverdue),
  };
}

/** Wire shape → domain shape (server-authoritative in API mode). */
export function preferencesFromApi(raw: ApiSchedulingPreferences): SchedulingPreferences {
  return normalizePreferences({
    availableMinutesPerDay: raw.available_minutes_per_day,
    dailyLimitMinutes: raw.daily_limit_minutes,
    bufferMinutes: raw.buffer_minutes,
    highCognitiveMaxPerDay: raw.high_cognitive_max_per_day,
    maxDailyMinutesPerGoal:
      raw.max_daily_minutes_per_goal ?? DEFAULT_PREFERENCES.maxDailyMinutesPerGoal,
    sleepStart: raw.sleep_start ?? DEFAULT_PREFERENCES.sleepStart,
    sleepEnd: raw.sleep_end ?? DEFAULT_PREFERENCES.sleepEnd,
    feedbackTime: raw.feedback_time ?? null,
    feedbackEnabled: raw.feedback_enabled ?? DEFAULT_PREFERENCES.feedbackEnabled,
    autoBacklogOverdue:
      raw.auto_backlog_overdue ?? DEFAULT_PREFERENCES.autoBacklogOverdue,
  });
}

/** Domain shape → wire shape for `PUT /users/me/preferences`. */
export function preferencesToApi(
  preferences: SchedulingPreferences,
): ApiSchedulingPreferences {
  return {
    available_minutes_per_day: preferences.availableMinutesPerDay,
    daily_limit_minutes: preferences.dailyLimitMinutes,
    buffer_minutes: preferences.bufferMinutes,
    high_cognitive_max_per_day: preferences.highCognitiveMaxPerDay,
    max_daily_minutes_per_goal: preferences.maxDailyMinutesPerGoal,
    sleep_start: preferences.sleepStart,
    sleep_end: preferences.sleepEnd,
    feedback_time: preferences.feedbackTime,
    feedback_enabled: preferences.feedbackEnabled,
    auto_backlog_overdue: preferences.autoBacklogOverdue,
  };
}
