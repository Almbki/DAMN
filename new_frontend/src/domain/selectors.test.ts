import { describe, expect, it } from 'vitest';

import { buildLists, countLists } from '@/domain/selectors';
import type { Task } from '@/domain/task';

const TODAY = '2026-10-27';

function task(overrides: Partial<Task>): Task {
  return {
    id: 1,
    title: '任务',
    description: '',
    notes: '',
    goalId: null,
    priority: 2,
    done: false,
    skipped: false,
    startDate: null,
    startTime: null,
    dueDate: null,
    dueTime: null,
    endTime: null,
    estimatedMinutes: null,
    actualMinutes: null,
    cognitiveLoad: 'medium',
    repeat: { freq: 'none', interval: 1, end: 'never', until: null, count: null },
    taskKind: 'one_off',
    seriesId: null,
    seriesIndex: null,
    occurrenceDate: null,
    targetAmount: null,
    targetUnit: null,
    tags: [],
    order: 0,
    completedAt: null,
    standards: [],
    completionProbability: null,
    predictedDuration: null,
    isFlexible: true,
    ...overrides,
  };
}

describe('smart lists and missed occurrences', () => {
  const legacyOverdue = task({ id: 1, dueDate: '2026-10-20' });
  const flaggedOverdue = task({ id: 2, overdue: true });
  const missed = task({ id: 3, missed: true, dueDate: '2026-10-26', taskKind: 'routine' });
  const completed = task({ id: 4, done: true, dueDate: '2026-10-20' });
  const backlogToday = task({ id: 5, backlog: true, dueDate: TODAY });
  const backlogTomorrow = task({ id: 6, backlog: true, dueDate: '2026-10-28' });
  const backlogFuture = task({ id: 7, backlog: true, dueDate: '2026-11-03' });
  const backlogPast = task({ id: 8, backlog: true, dueDate: '2026-10-20' });
  const backlogUndated = task({ id: 9, backlog: true });
  const baseTasks = [legacyOverdue, flaggedOverdue, missed, completed];
  const lists = buildLists(baseTasks, TODAY);
  const withBacklog = buildLists(
    [...baseTasks, backlogToday, backlogTomorrow, backlogFuture, backlogPast, backlogUndated],
    TODAY,
  );

  it('includes backend-flagged and legacy-date overdue tasks', () => {
    expect(lists.overdue.map((item) => item.id)).toEqual([1, 2]);
  });

  it('never puts a missed occurrence in open smart lists', () => {
    expect(lists.overdue).not.toContainEqual(missed);
    expect(lists.upcoming).not.toContainEqual(missed);
    expect(lists.noDate).not.toContainEqual(missed);
    expect(lists.tomorrow).not.toContainEqual(missed);
  });

  it('keeps missed tasks out of smart-list counts', () => {
    expect(countLists(lists).overdue).toBe(2);
    expect(countLists(lists).all).toBe(2);
  });

  it('does not show completed tasks in the overdue list', () => {
    expect(lists.overdue.map((item) => item.id)).not.toContain(4);
  });

  it('keeps explicit backlog tasks out of every smart list', () => {
    const backlogIds = [5, 6, 7, 8, 9];
    for (const key of ['today', 'tomorrow', 'upcoming', 'overdue', 'noDate'] as const) {
      const ids = withBacklog[key].map((item) => item.id);
      for (const id of backlogIds) expect(ids).not.toContain(id);
    }
    // Only the dated checks changed; the legitimately undated open task stays.
    expect(countLists(withBacklog).noDate).toBe(countLists(lists).noDate);
  });
});
