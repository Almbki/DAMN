import { addDays, parseISO, todayISO } from '@/domain/date';
import type { Goal } from '@/domain/goal';
import { isClosed, type Task } from '@/domain/task';

export type SmartListKey = 'all' | 'today' | 'tomorrow' | 'upcoming' | 'overdue' | 'noDate';

export const SMART_LIST_KEYS: SmartListKey[] = [
  'all',
  'today',
  'tomorrow',
  'upcoming',
  'overdue',
  'noDate',
];

export type RulerSegmentState = 'done' | 'now' | 'todo';

export function buildLists(
  tasks: Task[],
  today: string = todayISO(),
): Record<SmartListKey, Task[]> {
  const tomorrow = addDays(today, 1);
  const open = (task: Task) => !isClosed(task);
  return {
    all: tasks,
    today: tasks.filter((task) => task.dueDate === today),
    tomorrow: tasks.filter((task) => task.dueDate === tomorrow && open(task)),
    upcoming: tasks.filter((task) => task.dueDate && task.dueDate > tomorrow && open(task)),
    overdue: tasks.filter((task) => task.dueDate && task.dueDate < today && open(task)),
    noDate: tasks.filter((task) => !task.dueDate && open(task)),
  };
}

export function countLists(lists: Record<SmartListKey, Task[]>): Record<SmartListKey, number> {
  const counts = {} as Record<SmartListKey, number>;
  SMART_LIST_KEYS.forEach((key) => {
    counts[key] = lists[key].filter((task) => !isClosed(task)).length;
  });
  return counts;
}

/** Monday of the week containing `date`. */
export function startOfWeek(date: string): string {
  const dow = parseISO(date).getDay();
  return addDays(date, -((dow + 6) % 7));
}

/** Monday..Sunday of the week containing `date`. */
export function weekDates(date: string): string[] {
  const start = startOfWeek(date);
  return Array.from({ length: 7 }, (_, index) => addDays(start, index));
}

export interface GoalGroup {
  goal: Goal | null;
  tasks: Task[];
}

/** Group tasks by their owning goal, preserving the goal list order. */
export function groupByGoal(tasks: Task[], goals: Goal[]): GoalGroup[] {
  const groups: GoalGroup[] = goals.map((goal) => ({
    goal,
    tasks: tasks.filter((task) => task.goalId === goal.id),
  }));
  const orphans = tasks.filter(
    (task) => task.goalId == null || !goals.some((goal) => goal.id === task.goalId),
  );
  if (orphans.length > 0) groups.push({ goal: null, tasks: orphans });
  return groups;
}

export function pickCurrentTask(tasks: Task[], today: string = todayISO()): Task | null {
  const todayOpen = tasks.filter((task) => task.dueDate === today && !isClosed(task));
  return todayOpen[0] ?? tasks.find((task) => !isClosed(task)) ?? null;
}

export function buildRuler(
  tasks: Task[],
  currentId: number | null | undefined,
  today: string = todayISO(),
): { key: string; state: RulerSegmentState }[] {
  const todays = tasks.filter((task) => task.dueDate === today);
  const base = todays.length > 0 ? todays : tasks.filter((task) => !isClosed(task));
  return base.map((task) => ({
    key: String(task.id),
    state: isClosed(task) ? 'done' : task.id === currentId ? 'now' : 'todo',
  }));
}
