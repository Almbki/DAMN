import { describe, expect, it } from 'vitest';

import type { FeedbackObligationRead } from '@/api/types';
import {
  feedbackObligationForDate,
  nextFeedbackObligation,
  retrospectiveDayCount,
  retrospectiveDebtLabel,
  retrospectiveObligations,
} from '@/domain/feedback-obligation';

const TODAY = '2026-10-27';

function obligation(
  executionDate: string,
  overrides: Partial<FeedbackObligationRead> = {},
): FeedbackObligationRead {
  return {
    execution_date: executionDate,
    status: 'pending_feedback',
    is_retrospective: executionDate < TODAY,
    plan_id: 12,
    ...overrides,
  };
}

describe('feedback obligations', () => {
  const list = [
    obligation('2026-10-26'),
    obligation('2026-10-24'),
    obligation(TODAY),
  ];

  it('chooses the oldest unresolved day', () => {
    expect(nextFeedbackObligation(list)?.execution_date).toBe('2026-10-24');
    expect(nextFeedbackObligation([])).toBeNull();
  });

  it('lists retrospective days oldest first', () => {
    expect(retrospectiveObligations(list, TODAY).map((item) => item.execution_date)).toEqual([
      '2026-10-24',
      '2026-10-26',
    ]);
  });

  it('uses the date when the backend flag has gone stale', () => {
    const stale = obligation('2026-10-25', { is_retrospective: false });
    expect(retrospectiveObligations([stale], TODAY)).toHaveLength(1);
  });

  it('counts distinct outstanding days and labels them', () => {
    expect(retrospectiveDayCount(list, TODAY)).toBe(2);
    expect(retrospectiveDebtLabel(2)).toBe('还有 2 天的反馈没有补填');
    expect(retrospectiveDebtLabel(0)).toBe('');
  });

  it('finds the obligation for a specific day', () => {
    expect(feedbackObligationForDate(list, TODAY)?.plan_id).toBe(12);
    expect(feedbackObligationForDate(list, '2026-10-20')).toBeNull();
  });
});
