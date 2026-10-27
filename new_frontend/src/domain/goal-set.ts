/** Client-side view of a goal set's lifecycle. Mirrors the backend enum. */
export type GoalSetStatus = 'active' | 'archived';

export type GoalSetFilter = 'active' | 'archived' | 'all';

export const GOAL_SET_FILTERS: { key: GoalSetFilter; label: string }[] = [
  { key: 'active', label: '进行中' },
  { key: 'archived', label: '已归档' },
  { key: 'all', label: '全部' },
];

/** The fields the list/filter helpers need; `GoalSetRead` satisfies this. */
export interface GoalSetSummary {
  status: GoalSetStatus;
  goal_count: number;
  incomplete_goal_count: number;
}

export function filterGoalSets<T extends GoalSetSummary>(
  sets: T[],
  filter: GoalSetFilter,
): T[] {
  if (filter === 'all') return sets;
  return sets.filter((set) => set.status === filter);
}

export function goalSetFilterCounts(
  sets: GoalSetSummary[],
): Record<GoalSetFilter, number> {
  return {
    active: sets.filter((set) => set.status === 'active').length,
    archived: sets.filter((set) => set.status === 'archived').length,
    all: sets.length,
  };
}

export function goalSetStatusLabel(status: GoalSetStatus): string {
  return status === 'archived' ? '已归档' : '进行中';
}

export function goalSetCountsLabel(
  set: Pick<GoalSetSummary, 'goal_count' | 'incomplete_goal_count'>,
): string {
  return `${set.goal_count} 个目标 · ${set.incomplete_goal_count} 个未完成`;
}

/** Archived sets are read-only for grouping: no attaching new goals. */
export function canAttachGoals(status: GoalSetStatus): boolean {
  return status === 'active';
}
