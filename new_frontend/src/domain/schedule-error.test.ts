import { describe, expect, it } from 'vitest';

import { schedulingErrorMessage } from '@/domain/schedule-error';

describe('schedulingErrorMessage', () => {
  it('maps stable reason codes to grounded Chinese copy', () => {
    expect(
      schedulingErrorMessage({
        detail: { reason_code: 'fixed_event_overlap', message: 'overlaps event' },
      }),
    ).toBe('与固定日程冲突');
    expect(
      schedulingErrorMessage({ detail: { reason_code: 'LOCAL_RESCHEDULE_INFEASIBLE' } }),
    ).toBe('按当前约束无法仅通过顺延完成后续任务');
  });

  it('falls back to the server message for an unknown code', () => {
    expect(
      schedulingErrorMessage({
        detail: { reason_code: 'SOMETHING_NEW', message: '服务端说明' },
      }),
    ).toBe('服务端说明');
    expect(schedulingErrorMessage({ message: '服务暂时不可用' })).toBe('服务暂时不可用');
  });

  it('uses a safe fallback when nothing useful is present', () => {
    expect(schedulingErrorMessage(null)).toBe('安排没有完成，请稍后再试。');
  });
});
