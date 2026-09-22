import { Platform } from 'react-native';

import { dataSource } from '@/api/config';
import { getPreferences, putPreferences } from '@/api/endpoints';
import { DEFAULT_PREFERENCES, type SchedulingPreferences } from '@/domain/preferences';

/**
 * Persistence for scheduling preferences. In api mode the backend is the source
 * of truth (`GET`/`PUT /users/me/preferences`); local storage stays as an
 * offline cache so the UI has a value immediately and still works when the
 * server is unreachable. Mock mode is local-only.
 */
const KEY = 'damn.preferences';
const isWeb = Platform.OS === 'web';

/** Wire shape of the preferences endpoints (`snake_case`, backend `SchedulingPreferences`). */
type ApiPreferences = {
  available_minutes_per_day: number;
  daily_limit_minutes: number;
  buffer_minutes: number;
  high_cognitive_max_per_day: number;
  sleep_start?: string | null;
  sleep_end?: string | null;
};

function fromApi(raw: ApiPreferences): SchedulingPreferences {
  return {
    availableMinutesPerDay: raw.available_minutes_per_day,
    dailyLimitMinutes: raw.daily_limit_minutes,
    bufferMinutes: raw.buffer_minutes,
    highCognitiveMaxPerDay: raw.high_cognitive_max_per_day,
    sleepStart: raw.sleep_start ?? DEFAULT_PREFERENCES.sleepStart,
    sleepEnd: raw.sleep_end ?? DEFAULT_PREFERENCES.sleepEnd,
  };
}

function toApi(preferences: SchedulingPreferences): ApiPreferences {
  return {
    available_minutes_per_day: preferences.availableMinutesPerDay,
    daily_limit_minutes: preferences.dailyLimitMinutes,
    buffer_minutes: preferences.bufferMinutes,
    high_cognitive_max_per_day: preferences.highCognitiveMaxPerDay,
    sleep_start: preferences.sleepStart,
    sleep_end: preferences.sleepEnd,
  };
}

export function loadPreferences(): SchedulingPreferences {
  if (!isWeb) return DEFAULT_PREFERENCES;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return DEFAULT_PREFERENCES;
    return { ...DEFAULT_PREFERENCES, ...(JSON.parse(raw) as Partial<SchedulingPreferences>) };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function savePreferences(preferences: SchedulingPreferences): void {
  if (!isWeb) return;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(preferences));
  } catch {
    // Persistence is best-effort; the in-memory value is still correct.
  }
}

/**
 * Load preferences for the running data source. api mode reads the server and
 * refreshes the offline cache, falling back to the cache on failure. mock mode
 * returns the cache unchanged.
 */
export async function loadPreferencesRemote(): Promise<SchedulingPreferences> {
  const cached = loadPreferences();
  if (dataSource !== 'api') return cached;
  try {
    const next = fromApi(await getPreferences());
    savePreferences(next);
    return next;
  } catch {
    return cached;
  }
}

/**
 * Persist preferences. The offline cache is always written; api mode also
 * write-throughs to the server best-effort, silently keeping the local value if
 * the request fails.
 */
export async function savePreferencesRemote(preferences: SchedulingPreferences): Promise<void> {
  savePreferences(preferences);
  if (dataSource !== 'api') return;
  try {
    await putPreferences(toApi(preferences));
  } catch {
    // Offline cache keeps the value; the next change retries.
  }
}
