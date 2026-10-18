import { hhmm } from '@/api/format';
import type { ScheduleEventRead } from '@/api/types';
import { addDays, parseISO } from '@/domain/date';

/** Backend weekday indices are 0 = Monday … 6 = Sunday. */
export const WEEKDAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] as const;

export function weekdayIndex(date: string): number {
  return (parseISO(date).getDay() + 6) % 7;
}

export function monthDay(date: string): string {
  const parsed = parseISO(date);
  return `${parsed.getMonth() + 1}/${parsed.getDate()}`;
}

export function longDate(date: string): string {
  const parsed = parseISO(date);
  return `${parsed.getFullYear()}年${parsed.getMonth() + 1}月${parsed.getDate()}日`;
}

export function eventTimeRange(event: ScheduleEventRead): string {
  return `${hhmm(event.start_time)}–${hhmm(event.end_time)}`;
}

/** "2026年10月12日 – 10月18日" (the second year is shown only across years). */
export function formatWeekRange(weekStart: string): string {
  const start = parseISO(weekStart);
  const endDate = addDays(weekStart, 6);
  const end = parseISO(endDate);
  const startLabel = `${start.getFullYear()}年${start.getMonth() + 1}月${start.getDate()}日`;
  const endLabel =
    end.getFullYear() !== start.getFullYear()
      ? `${end.getFullYear()}年${end.getMonth() + 1}月${end.getDate()}日`
      : end.getMonth() !== start.getMonth()
        ? `${end.getMonth() + 1}月${end.getDate()}日`
        : `${end.getDate()}日`;
  return `${startLabel} – ${endLabel}`;
}

/**
 * One human sentence for the detail dialog: weekly recurrences include their
 * weekday list, one-offs include their date or date range.
 */
export function formatEventWhen(event: ScheduleEventRead): string {
  const time = eventTimeRange(event);
  const start = event.start_date ? event.start_date.slice(0, 10) : null;
  const end = event.end_date ? event.end_date.slice(0, 10) : null;
  const weekdays = (event.weekdays ?? []).filter((day) => day >= 0 && day <= 6);

  if (weekdays.length > 0) {
    const days = weekdays.map((day) => WEEKDAY_LABELS[day].slice(1)).join('、');
    const recurrence = `每周${days} ${time}`;
    if (!start) return recurrence;
    const bounds =
      end == null
        ? `${longDate(start)} 起`
        : end === start
          ? longDate(start)
          : `${longDate(start)} – ${longDate(end)}`;
    return `${bounds} · ${recurrence}`;
  }

  if (start) {
    const dayLabel =
      end && end !== start ? `${longDate(start)} – ${longDate(end)}` : longDate(start);
    return `${dayLabel} · ${time}`;
  }

  return time;
}
