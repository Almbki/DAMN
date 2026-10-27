import { describe, expect, it } from 'vitest';

import { PLAN_LOCK_MESSAGE, isPlanEditingLocked } from '@/domain/plan-lock';

describe('isPlanEditingLocked', () => {
  it.each([
    [false, false, false],
    [false, true, true],
    [true, false, true],
    [true, true, true],
  ])(
    'previewBusy=%s hasPreview=%s → %s',
    (previewBusy, hasPreview, expected) => {
      expect(isPlanEditingLocked({ previewBusy, hasPreview })).toBe(expected);
    },
  );

  it('uses one shared message', () => {
    expect(PLAN_LOCK_MESSAGE).toBe('请先完成当前计划');
  });
});
