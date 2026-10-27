import { describe, expect, it } from 'vitest';

import {
  canAttachGoals,
  filterGoalSets,
  goalSetCountsLabel,
  goalSetFilterCounts,
  goalSetStatusLabel,
  type GoalSetSummary,
} from '@/domain/goal-set';

const sets: GoalSetSummary[] = [
  { status: 'active', goal_count: 3, incomplete_goal_count: 2 },
  { status: 'active', goal_count: 1, incomplete_goal_count: 0 },
  { status: 'archived', goal_count: 4, incomplete_goal_count: 1 },
];

describe('goal set filtering', () => {
  it('defaults the active filter to active sets only', () => {
    expect(filterGoalSets(sets, 'active')).toHaveLength(2);
    expect(filterGoalSets(sets, 'archived')).toHaveLength(1);
    expect(filterGoalSets(sets, 'all')).toHaveLength(3);
  });

  it('counts each filter bucket', () => {
    expect(goalSetFilterCounts(sets)).toEqual({ active: 2, archived: 1, all: 3 });
  });
});

describe('goal set copy', () => {
  it('labels both lifecycle states', () => {
    expect(goalSetStatusLabel('active')).toBe('进行中');
    expect(goalSetStatusLabel('archived')).toBe('已归档');
  });

  it('summarises goal and incomplete counts', () => {
    expect(goalSetCountsLabel(sets[0])).toBe('3 个目标 · 2 个未完成');
    expect(goalSetCountsLabel(sets[1])).toBe('1 个目标 · 0 个未完成');
  });

  it('never offers attaching into an archived set', () => {
    expect(canAttachGoals('active')).toBe(true);
    expect(canAttachGoals('archived')).toBe(false);
  });
});
