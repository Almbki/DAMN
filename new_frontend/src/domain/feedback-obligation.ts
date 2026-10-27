import type { FeedbackObligationRead } from '@/api/types';

/**
 * Pure helpers over the backend's unresolved feedback debts.
 *
 * The endpoint already returns them oldest first; keeping the selection here
 * makes the gate, the feedback screen and the tests agree on the same rule.
 */
export function nextFeedbackObligation(
  obligations: readonly FeedbackObligationRead[],
): FeedbackObligationRead | null {
  let oldest: FeedbackObligationRead | null = null;
  for (const item of obligations) {
    if (oldest == null || item.execution_date < oldest.execution_date) oldest = item;
  }
  return oldest;
}

/**
 * Debts the user can only fill in later. We trust the backend flag and keep a
 * date comparison so a list fetched before midnight still surfaces.
 */
export function retrospectiveObligations(
  obligations: readonly FeedbackObligationRead[],
  today: string,
): FeedbackObligationRead[] {
  return obligations
    .filter((item) => item.is_retrospective || item.execution_date < today)
    .sort((a, b) => a.execution_date.localeCompare(b.execution_date));
}

/** Distinct retrospective days still waiting for a check-in. */
export function retrospectiveDayCount(
  obligations: readonly FeedbackObligationRead[],
  today: string,
): number {
  return new Set(
    retrospectiveObligations(obligations, today).map((item) => item.execution_date),
  ).size;
}

/** Grounded one-line label for the gate; empty when there is no debt. */
export function retrospectiveDebtLabel(days: number): string {
  return days > 0 ? `还有 ${days} 天的反馈没有补填` : '';
}

/** The obligation for one execution day, if the backend listed it. */
export function feedbackObligationForDate(
  obligations: readonly FeedbackObligationRead[],
  date: string,
): FeedbackObligationRead | null {
  return obligations.find((item) => item.execution_date === date) ?? null;
}
