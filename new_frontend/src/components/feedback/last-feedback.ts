import { Platform } from 'react-native';

import { todayISO } from '@/domain/date';

/**
 * The date of the last successful feedback submission.
 *
 * A submission can adopt a new plan version, which means the gate may see an
 * empty `feedbackHistory` for a moment (or a fresh plan's history). Keeping a
 * local marker makes sure the user is not asked to write the same day's
 * feedback twice. Web uses localStorage; native keeps it in memory for the
 * lifetime of the app.
 */
const KEY = 'damn.feedback.lastDate';
let nativeDate: string | null = null;

export function getLastFeedbackDate(): string | null {
  if (Platform.OS !== 'web') return nativeDate;
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw && /^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : null;
  } catch {
    return null;
  }
}

export function markFeedbackSubmitted(date: string = todayISO()): void {
  if (Platform.OS === 'web') {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(KEY, date);
    } catch {
      // Best-effort: the in-memory history still contains the submission.
    }
    return;
  }
  nativeDate = date;
}
