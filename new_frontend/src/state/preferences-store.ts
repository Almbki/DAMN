import { Platform } from 'react-native';

import { dataSource } from '@/api/config';
import { getPreferences, putPreferences } from '@/api/endpoints';
import {
  DEFAULT_PREFERENCES,
  normalizePreferences,
  preferencesFromApi,
  preferencesToApi,
  type ApiSchedulingPreferences,
  type SchedulingPreferences,
} from '@/domain/preferences';

/**
 * Persistence for scheduling preferences. In api mode the backend is the source
 * of truth (`GET`/`PUT /users/me/preferences`); local storage stays as an
 * offline cache so the UI has a value immediately and still works when the
 * server is unreachable. Mock mode is local-only.
 */
const KEY = 'damn.preferences';
const isWeb = Platform.OS === 'web';

/** Wire shape of the preferences endpoints (`snake_case`, backend `SchedulingPreferences`). */
type ApiPreferences = ApiSchedulingPreferences;

function fromApi(raw: ApiPreferences): SchedulingPreferences {
  return preferencesFromApi(raw);
}

function toApi(preferences: SchedulingPreferences): ApiPreferences {
  return preferencesToApi(preferences);
}

export function loadPreferences(): SchedulingPreferences {
  if (!isWeb) return DEFAULT_PREFERENCES;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return DEFAULT_PREFERENCES;
    return normalizePreferences({
      ...DEFAULT_PREFERENCES,
      ...(JSON.parse(raw) as Partial<SchedulingPreferences>),
    });
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
 * PUTs are serialised so rapid stepper clicks arrive in order; each call carries
 * the full (functional) next value, so the last write wins deterministically.
 */
let putQueue: Promise<unknown> = Promise.resolve();

/**
 * Persist preferences. The offline cache is always written; api mode also
 * write-throughs to the server. Resolves `false` when the server rejected the
 * update so the provider can surface it as `actionError`.
 */
export async function savePreferencesRemote(preferences: SchedulingPreferences): Promise<boolean> {
  savePreferences(preferences);
  if (dataSource !== 'api') return true;

  const request = putQueue.then(() => putPreferences(toApi(preferences)));
  putQueue = request.then(
    () => undefined,
    () => undefined,
  );
  try {
    await request;
    return true;
  } catch {
    // Offline cache keeps the value; the next change retries.
    return false;
  }
}
