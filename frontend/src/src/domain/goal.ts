import type { Task } from '@/domain/task';

export type GoalStatus = 'active' | 'draft' | 'completed' | 'archived' | 'cancelled';

export interface Goal {
  id: number;
  title: string;
  description: string;
  status: GoalStatus;
  deadline: string | null;
  estimatedMinutes: number | null;
  priority: number;
  createdAt: string;
}

export interface GoalProgress {
  completedMinutes: number;
  totalMinutes: number;
  completedTasks: number;
  totalTasks: number;
  /** 0..1 */
  ratio: number;
  /**
   * `time` when any child task has an estimate (time-weighted — splitting a
   * task into smaller ones does not move the bar), `count` otherwise.
   */
  basis: 'time' | 'count';
}

export function goalProgress(goalId: number, tasks: Task[]): GoalProgress {
  const mine = tasks.filter((task) => task.goalId === goalId);
  const totalMinutes = mine.reduce((sum, task) => sum + (task.estimatedMinutes ?? 0), 0);
  const completedMinutes = mine
    .filter((task) => task.done)
    .reduce((sum, task) => sum + (task.estimatedMinutes ?? 0), 0);
  const totalTasks = mine.length;
  const completedTasks = mine.filter((task) => task.done).length;

  const basis: GoalProgress['basis'] = totalMinutes > 0 ? 'time' : 'count';
  const ratio =
    basis === 'time'
      ? totalMinutes > 0
        ? completedMinutes / totalMinutes
        : 0
      : totalTasks > 0
        ? completedTasks / totalTasks
        : 0;

  return { completedMinutes, totalMinutes, completedTasks, totalTasks, ratio, basis };
}

export function isDraft(goal: Goal): boolean {
  return goal.status === 'draft';
}
