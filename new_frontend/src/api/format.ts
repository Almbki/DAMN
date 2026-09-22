/**
 * Date/time helpers.
 *
 * Two measured backend quirks these exist to absorb:
 *  - `"YYYY-MM-DD"` parses as UTC midnight, so `new Date(...)` can show the
 *    previous day in local time.
 *  - `"HH:MM:SS"` is not a Date at all; it must be sliced.
 */

export function hhmm(time: string | null | undefined): string {
  if (!time) return '';
  const parts = time.split(':');
  return parts.length >= 2 ? `${parts[0]}:${parts[1]}` : time;
}

export function formatDate(isoDate: string | null | undefined): string {
  if (!isoDate) return '';
  const [year, month, day] = isoDate.slice(0, 10).split('-');
  if (!year || !month || !day) return isoDate;
  return `${Number(month)} 月 ${Number(day)} 日`;
}

export function minutesLabel(minutes: number | null | undefined): string {
  if (minutes == null) return '—';
  return String(Math.round(minutes));
}
