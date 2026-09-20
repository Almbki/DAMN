import { addDays, daysAgoISO, todayISO } from '@/domain/date';
import type { Task } from '@/domain/task';

export interface Completion {
  id: number;
  taskId: number;
  date: string;
  minutes: number;
}

export function closedCount(tasks: Task[]): number {
  return tasks.filter((task) => task.done || task.skipped).length;
}

/** Done / (done + skipped). Open tasks do not drag the rate down. */
export function completionRate(tasks: Task[]): number {
  const done = tasks.filter((task) => task.done).length;
  const closed = closedCount(tasks);
  return closed === 0 ? 0 : done / closed;
}

export function completedToday(tasks: Task[]): number {
  const today = todayISO();
  return tasks.filter((task) => task.done && task.completedAt === today).length;
}

export function minutesInRange(completions: Completion[], from: string, to: string): number {
  return completions
    .filter((item) => item.date >= from && item.date <= to)
    .reduce((sum, item) => sum + (item.minutes || 0), 0);
}

/** Consecutive days with at least one completion, ending today or yesterday. */
export function currentStreak(completions: Completion[], today = todayISO()): number {
  const days = new Set(completions.map((item) => item.date));
  let cursor = days.has(today) ? today : addDays(today, -1);
  if (!days.has(cursor)) return 0;
  let streak = 0;
  while (days.has(cursor)) {
    streak += 1;
    cursor = addDays(cursor, -1);
  }
  return streak;
}

export function longestStreak(completions: Completion[]): number {
  const days = Array.from(new Set(completions.map((item) => item.date))).sort();
  let best = 0;
  let run = 0;
  let previous: string | null = null;
  for (const day of days) {
    run = previous && addDays(previous, 1) === day ? run + 1 : 1;
    best = Math.max(best, run);
    previous = day;
  }
  return best;
}

export interface Bucket {
  date: string;
  count: number;
  minutes: number;
}

/** Last `days` days, oldest first. */
export function dailyBuckets(completions: Completion[], days: number): Bucket[] {
  const today = todayISO();
  const result: Bucket[] = [];
  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const date = addDays(today, -offset);
    const items = completions.filter((item) => item.date === date);
    result.push({
      date,
      count: items.length,
      minutes: items.reduce((sum, item) => sum + (item.minutes || 0), 0),
    });
  }
  return result;
}

/** Last `months` calendar months, oldest first. Counts completions per month. */
export function monthlyBuckets(completions: Completion[], months: number): Bucket[] {
  const base = new Date();
  const result: Bucket[] = [];
  for (let offset = months - 1; offset >= 0; offset -= 1) {
    const start = new Date(base.getFullYear(), base.getMonth() - offset, 1);
    const monthKey = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, '0')}`;
    const items = completions.filter((item) => item.date.startsWith(monthKey));
    result.push({
      date: monthKey,
      count: items.length,
      minutes: items.reduce((sum, item) => sum + (item.minutes || 0), 0),
    });
  }
  return result;
}

/** Seed helper for the mock store. */
export function seedDate(daysBack: number): string {
  return daysAgoISO(daysBack);
}
