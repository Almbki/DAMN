/**
 * Local calendar helpers.
 *
 * Dates are plain `YYYY-MM-DD` strings interpreted in the **local** timezone.
 * Never use `new Date('YYYY-MM-DD')` (that parses as UTC midnight and can show
 * the previous day), and never pass `HH:MM:SS` to `Date`.
 */

export function parseISO(date: string): Date {
  const [year, month, day] = date.slice(0, 10).split('-').map(Number);
  return new Date(year, (month ?? 1) - 1, day ?? 1);
}

export function toISO(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function todayISO(): string {
  return toISO(new Date());
}

export function addDays(date: string, days: number): string {
  const next = parseISO(date);
  next.setDate(next.getDate() + days);
  return toISO(next);
}

export function addMonths(date: string, months: number): string {
  const next = parseISO(date);
  next.setMonth(next.getMonth() + months);
  return toISO(next);
}

/** Whole days from `a` to `b` (b - a). Negative means b is before a. */
export function diffDays(a: string, b: string): number {
  const ms = parseISO(b).getTime() - parseISO(a).getTime();
  return Math.round(ms / 86_400_000);
}

export function formatShort(date: string | null): string {
  if (!date) return '';
  const today = todayISO();
  const delta = diffDays(today, date);
  if (delta === 0) return '今天';
  if (delta === 1) return '明天';
  if (delta === 2) return '后天';
  if (delta === -1) return '昨天';
  if (delta < 0) return `逾期 ${-delta} 天`;
  const d = parseISO(date);
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日`;
}

/** Local YYYY-MM-DD for "days ago". */
export function daysAgoISO(days: number): string {
  return addDays(todayISO(), -days);
}
