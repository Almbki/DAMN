/**
 * Grounded Chinese copy for deterministic scheduling rejections.
 *
 * The backend returns a `reason_code` inside `detail`; the code is stable while
 * the human message may be technical, so prefer the code and fall back to the
 * server's own message only when we do not know it.
 */

const REASON_MESSAGES: Record<string, string> = {
  fixed_event_overlap: '与固定日程冲突',
  daily_limit: '当天可用时间不足',
  available_time: '当天可用时间不足',
  outside_available_window: '当天可用时间不足',
  GOAL_DAILY_CAPACITY_EXCEEDED: '该目标今天已达到每日上限',
  insufficient_buffer: '与相邻任务间隔不足',
  deadline_exceeded: '超过截止时间',
  earliest_start: '早于最早开始日期',
  high_cognitive_consecutive: '高认知任务限制',
  high_cognitive_daily_max: '高认知任务限制',
  PAST_DATE: '不能安排到过去',
  PAST_TIME: '不能安排到今天已过去的时间',
  RECURRING_WRONG_DAY: '重复任务只能调整当天时间',
  RECURRING_NOT_RESCHEDULABLE: '重复任务不能顺延',
  RECURRING_NOT_BACKLOGGABLE: '重复任务不能放入任务池',
  LOCAL_RESCHEDULE_INFEASIBLE: '按当前约束无法仅通过顺延完成后续任务',
};

export function schedulingReasonMessage(reasonCode: unknown): string | null {
  if (typeof reasonCode !== 'string') return null;
  return REASON_MESSAGES[reasonCode] ?? null;
}

/** Map an `ApiError`-shaped value to copy; unknown codes use the server message. */
export function schedulingErrorMessage(
  error: unknown,
  fallback = '安排没有完成，请稍后再试。',
): string {
  if (error && typeof error === 'object') {
    const detail = (error as { detail?: unknown }).detail;
    if (detail && typeof detail === 'object') {
      const reasonCode = (detail as { reason_code?: unknown }).reason_code;
      const mapped = schedulingReasonMessage(reasonCode);
      if (mapped) return mapped;

      const detailMessage = (detail as { message?: unknown }).message;
      if (typeof detailMessage === 'string' && detailMessage.trim()) {
        return detailMessage;
      }
    }

    const message = (error as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim()) return message;
  }
  return fallback;
}
