import { addDays, parseISO, toISO, todayISO } from '@/domain/date';

export interface QuickAddResult {
  title: string;
  dueDate?: string;
  dueTime?: string;
}

const WEEKDAY: Record<string, number> = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 日: 0, 天: 0 };

function nextWeekday(today: string, target: number, nextWeek: boolean): string {
  const dow = parseISO(today).getDay();
  if (nextWeek) {
    const toMonday = (8 - dow) % 7 || 7;
    return addDays(today, toMonday + (target === 0 ? 6 : target - 1));
  }
  let delta = (target - dow + 7) % 7;
  if (delta === 0) delta = 7;
  return addDays(today, delta);
}

/**
 * Minimal natural-language quick add for dates / time / priority. Intentionally
 * small: it strips only tokens it fully understands and leaves the rest as the
 * title. No network, no model, no surprises.
 */
export function parseQuickAdd(input: string, today = todayISO()): QuickAddResult {
  let text = ` ${input.trim()} `;
  let dueDate: string | undefined;
  let dueTime: string | undefined;

  const timeMatch = text.match(/(\d{1,2})[:：](\d{2})/);
  if (timeMatch) {
    const hour = String(Math.min(23, Number(timeMatch[1]))).padStart(2, '0');
    dueTime = `${hour}:${timeMatch[2]}`;
    text = text.replace(timeMatch[0], ' ');
  }

  const isoMatch = text.match(/(\d{4}-\d{2}-\d{2})/);
  if (isoMatch) {
    dueDate = isoMatch[1];
    text = text.replace(isoMatch[0], ' ');
  }

  if (!dueDate) {
    const monthDay = text.match(/(\d{1,2})月(\d{1,2})[日号]/);
    if (monthDay) {
      const year = parseISO(today).getFullYear();
      dueDate = toISO(new Date(year, Number(monthDay[1]) - 1, Number(monthDay[2])));
      text = text.replace(monthDay[0], ' ');
    }
  }

  if (!dueDate) {
    const nextWeekMatch = text.match(/下(?:周|星期)([一二三四五六日天])/);
    const weekMatch = text.match(/(?:周|星期)([一二三四五六日天])/);
    if (/今天/.test(text)) {
      dueDate = today;
      text = text.replace(/今天/, ' ');
    } else if (/后天/.test(text)) {
      dueDate = addDays(today, 2);
      text = text.replace(/后天/, ' ');
    } else if (/明天/.test(text)) {
      dueDate = addDays(today, 1);
      text = text.replace(/明天/, ' ');
    } else if (nextWeekMatch) {
      dueDate = nextWeekday(today, WEEKDAY[nextWeekMatch[1]], true);
      text = text.replace(nextWeekMatch[0], ' ');
    } else if (weekMatch) {
      dueDate = nextWeekday(today, WEEKDAY[weekMatch[1]], false);
      text = text.replace(weekMatch[0], ' ');
    }
  }

  return {
    title: text.replace(/\s+/g, ' ').trim(),
    dueDate,
    dueTime,
  };
}
