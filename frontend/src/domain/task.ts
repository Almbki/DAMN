import { addDays, addMonths } from '@/domain/date';

/**
 * The frontend task model.
 *
 * Deliberately richer than the FastAPI contract in `api/types.ts`:
 * `docs/api.md` only exposes task PATCH, so dates, recurrence and notes live
 * here as local state until the backend grows endpoints for them.
 */

export type RepeatFreq = 'none' | 'daily' | 'weekly' | 'monthly' | 'custom';
export type RepeatEnd = 'never' | 'until' | 'count';
export type CognitiveLoad = 'low' | 'medium' | 'high';

export interface Repeat {
  freq: RepeatFreq;
  /** Every N days/weeks/months (custom = every N days). */
  interval: number;
  end: RepeatEnd;
  until: string | null;
  /** Remaining occurrences when `end === 'count'`. */
  count: number | null;
}

export interface Task {
  id: number;
  title: string;
  description: string;
  notes: string;
  /** Owning goal, from backend `TaskRead.goal_id` (trustworthy). */
  goalId: number | null;
  /** 1 low · 2 medium · 3 high. Mirrors backend `priority`, clamped for display. */
  priority: number;
  done: boolean;
  /** "今天先不做" — a soft defer, not a failure. */
  skipped: boolean;
  startDate: string | null;
  startTime: string | null;
  dueDate: string | null;
  dueTime: string | null;
  /** Local clock `HH:MM` the task ends, when the backend provides it. */
  endTime: string | null;
  estimatedMinutes: number | null;
  actualMinutes: number | null;
  /** Mirrors the backend `cognitive_load`; drives the insight panel. */
  cognitiveLoad: CognitiveLoad;
  repeat: Repeat;
  tags: string[];
  /** Display order inside a list. Lower comes first. */
  order: number;
  /** Local date (YYYY-MM-DD) the task was last completed, for streak/stats. */
  completedAt: string | null;
}

export const REPEAT_FREQS: RepeatFreq[] = ['none', 'daily', 'weekly', 'monthly', 'custom'];
export const REPEAT_ENDS: RepeatEnd[] = ['never', 'until', 'count'];

export const REPEAT_FREQ_LABEL: Record<RepeatFreq, string> = {
  none: '不重复',
  daily: '每天',
  weekly: '每周',
  monthly: '每月',
  custom: '自定义',
};

export const REPEAT_END_LABEL: Record<RepeatEnd, string> = {
  never: '一直重复',
  until: '到某天结束',
  count: '重复 N 次',
};

export const NO_REPEAT: Repeat = {
  freq: 'none',
  interval: 1,
  end: 'never',
  until: null,
  count: null,
};

export function repeatLabel(repeat: Repeat): string {
  if (repeat.freq === 'none') return '';
  const base =
    repeat.freq === 'custom'
      ? `每 ${repeat.interval} 天`
      : repeat.interval > 1
        ? `每 ${repeat.interval} ${repeat.freq === 'daily' ? '天' : repeat.freq === 'weekly' ? '周' : '个月'}`
        : REPEAT_FREQ_LABEL[repeat.freq];
  if (repeat.end === 'until' && repeat.until) return `${base}，到 ${repeat.until}`;
  if (repeat.end === 'count' && repeat.count != null) return `${base}，剩 ${repeat.count} 次`;
  return base;
}

/** Next occurrence date for a repeating task, or null when the series ends. */
export function nextOccurrence(task: Task): string | null {
  const repeat = task.repeat;
  if (repeat.freq === 'none' || !task.dueDate) return null;
  if (repeat.end === 'count' && (repeat.count ?? 0) <= 0) return null;

  const step = Math.max(1, repeat.interval);
  const next =
    repeat.freq === 'daily' || repeat.freq === 'custom'
      ? addDays(task.dueDate, step)
      : repeat.freq === 'weekly'
        ? addDays(task.dueDate, step * 7)
        : addMonths(task.dueDate, step);

  if (repeat.end === 'until' && repeat.until && next > repeat.until) return null;
  return next;
}

/**
 * FastAPI `TaskStatus` values: done → completed, skipped → skipped, otherwise
 * pending. Used when the HTTP adapter is wired up.
 */
export function toApiStatus(task: Task): string {
  if (task.done) return 'completed';
  if (task.skipped) return 'skipped';
  return 'pending';
}

export function isClosed(task: Task): boolean {
  return task.done || task.skipped;
}
