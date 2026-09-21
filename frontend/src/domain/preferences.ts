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
}

export const DEFAULT_PREFERENCES: SchedulingPreferences = {
  availableMinutesPerDay: 480,
  dailyLimitMinutes: 300,
  bufferMinutes: 15,
  highCognitiveMaxPerDay: 2,
  sleepStart: '23:30',
  sleepEnd: '07:30',
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
