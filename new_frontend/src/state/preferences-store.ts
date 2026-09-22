import { Platform } from 'react-native';

import { DEFAULT_PREFERENCES, type SchedulingPreferences } from '@/domain/preferences';

/**
 * Local persistence for scheduling preferences. The backend can store them in
 * `User.profile` but `POST /plans/generate` does not read them yet
 * (docs/design/backend-api-gaps.md §7), so the client owns them for now.
 */
const KEY = 'damn.preferences';
const isWeb = Platform.OS === 'web';

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
