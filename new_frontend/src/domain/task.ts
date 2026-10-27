import { addDays, addMonths, todayISO } from '@/domain/date';

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

/** Mirrors the backend `TaskKind` (how a task *instance* behaves). */
export type TaskKind = 'one_off' | 'long_term' | 'routine';

/** Product-level four-way goal planning mode (backend `PlanningMode`). */
export type PlanningMode = 'one_off' | 'recurring' | 'project' | 'project_recurring';
export type RecurrenceFrequency = 'daily' | 'weekly';

export const TASK_KIND_LABEL: Record<TaskKind, string> = {
  one_off: '一次性',
  long_term: '长期',
  routine: '常规',
};

export const PLANNING_MODE_LABEL: Record<PlanningMode, string> = {
  one_off: '一次性',
  recurring: '重复习惯',
  project: '项目/课程',
  project_recurring: '项目 + 节奏',
};

/** Legacy fallback only: new payloads carry `planning_mode` explicitly. */
export function planningModeFromTaskKind(
  kind: TaskKind | null | undefined,
): PlanningMode {
  if (kind === 'routine' || kind === 'long_term') return 'recurring';
  return 'one_off';
}

/** Legacy field kept in sync for older backend paths. */
export function taskKindFromPlanningMode(mode: PlanningMode): TaskKind {
  if (mode === 'one_off') return 'one_off';
  if (mode === 'recurring') return 'routine';
  return 'long_term';
}

/** Backend goal types use different names than task kinds. */
export function taskKindFromGoalType(goalType: string | null | undefined): TaskKind {
  if (goalType === 'long_term') return 'long_term';
  if (goalType === 'habit') return 'routine';
  return 'one_off';
}

/** Inverse of `taskKindFromGoalType`; `undefined` keeps the backend default. */
export function goalTypeFromTaskKind(kind: TaskKind | null | undefined): string | undefined {
  if (kind === 'long_term') return 'long_term';
  if (kind === 'routine') return 'habit';
  if (kind === 'one_off') return 'short_term';
  return undefined;
}

export interface Repeat {
  freq: RepeatFreq;
  /** Every N days/weeks/months (custom = every N days). */
  interval: number;
  end: RepeatEnd;
  until: string | null;
  /** Remaining occurrences when `end === 'count'`. */
  count: number | null;
}

/** A sub-standard (`TaskStandardRead`): a checklist item inside a task. */
export interface TaskStandard {
  id: number;
  description: string;
  estimatedDuration: number | null;
  completed: boolean;
  orderIndex: number;
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
  /** Backend `overdue`: a past one-off task that is still open. */
  overdue?: boolean;
  /** Backend `missed`: a past recurring occurrence; closed but not completed. */
  missed?: boolean;
  /** Backend `backlog`: explicitly unscheduled and kept in the 任务池. */
  backlog?: boolean;
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
  /** How the task repeats over time (`TaskRead.task_kind`). */
  taskKind: TaskKind;
  /** Backend series identity for `long_term` / `routine` occurrences. */
  seriesId: string | null;
  seriesIndex: number | null;
  /** The occurrence day inside a series (`TaskRead.occurrence_date`). */
  occurrenceDate: string | null;
  /** Optional quantity target, e.g. 3 × `次/周`. */
  targetAmount: number | null;
  targetUnit: string | null;
  tags: string[];
  /** Display order inside a list. Lower comes first. */
  order: number;
  /** Local date (YYYY-MM-DD) the task was last completed, for streak/stats. */
  completedAt: string | null;
  /** Checklist items from `TaskRead.standards`. */
  standards: TaskStandard[];
  /** ML completion probability (`TaskRead.completion_probability`), 0..1. */
  completionProbability: number | null;
  /** ML predicted duration in minutes (`TaskRead.predicted_duration`). */
  predictedDuration: number | null;
  /** Truthful provenance of the production estimate. */
  predictionSource?: string | null;
  predictionMode?: string | null;
  /** Local start timestamp for execution capture (not persisted on TaskRead). */
  startedAt?: string | null;
  /** Whether the scheduler may move this task (`TaskRead.is_flexible`). */
  isFlexible: boolean;
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
  // A missed occurrence is a historical fact: it no longer belongs in open
  // lists or actions, but it is NOT done and must not look completed.
  return task.done || task.skipped || task.missed === true;
}

/** Only the explicit backend status counts; never infer from a null date. */
export function isBacklog(task: Task): boolean {
  return task.backlog === true;
}

/** Tray items the user can still act on; completed/skipped/missed stay out. */
export function openBacklogTasks(tasks: Task[]): Task[] {
  return tasks.filter((task) => isBacklog(task) && !isClosed(task));
}

/**
 * A past task that still needs attention. The backend's `overdue` flag is
 * authoritative; mock/legacy rows fall back to the scheduled date.
 */
export function isOverdue(task: Task, today: string = todayISO()): boolean {
  if (isClosed(task) || isBacklog(task)) return false;
  if (task.overdue === true) return true;
  return task.dueDate != null && task.dueDate < today;
}

/**
 * A task belongs to a repeating series when the backend tagged it with a
 * `series_id`, or when its kind is anything other than one-off (legacy rows
 * that predate `series_id`).
 */
export function isRecurringSeriesTask(
  task: Pick<Task, 'seriesId' | 'taskKind'>,
): boolean {
  return task.seriesId != null || task.taskKind !== 'one_off';
}

/**
 * Every task that shares a series with `task`. The backend's `series_id` is the
 * identity; legacy rows without one fall back to the same goal + task kind.
 * A non-series task resolves to itself.
 */
export function seriesTasks(
  tasks: Task[],
  task: Pick<Task, 'id' | 'seriesId' | 'taskKind' | 'goalId'>,
): Task[] {
  if (!isRecurringSeriesTask(task)) return tasks.filter((item) => item.id === task.id);
  if (task.seriesId != null) {
    return tasks.filter((item) => item.seriesId === task.seriesId);
  }
  if (task.goalId != null) {
    return tasks.filter(
      (item) => item.goalId === task.goalId && item.taskKind === task.taskKind,
    );
  }
  return tasks.filter((item) => item.id === task.id);
}
