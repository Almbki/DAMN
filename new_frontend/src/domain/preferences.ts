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
  /** Local clock, `HH:MM`. */
  sleepStart: string;
  sleepEnd: string;
  /** Local clock, `HH:MM`; `null` until the user picks a reminder time. */
  feedbackTime: string | null;
  /** Whether the daily feedback reminder is enabled. */
  feedbackEnabled: boolean;
}

export const DEFAULT_PREFERENCES: SchedulingPreferences = {
  availableMinutesPerDay: 480,
  dailyLimitMinutes: 300,
  bufferMinutes: 15,
  highCognitiveMaxPerDay: 2,
  sleepStart: '23:30',
  sleepEnd: '07:30',
  feedbackTime: null,
  feedbackEnabled: false,
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
  };
}
