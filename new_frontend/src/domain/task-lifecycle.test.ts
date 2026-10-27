import { describe, expect, it } from 'vitest';

import { isBacklog, isClosed, isOverdue, type Task } from '@/domain/task';

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

describe('isClosed', () => {
  it('treats a missed occurrence as closed', () => {
    expect(isClosed(task({ missed: true }))).toBe(true);
  });

  it('does not make missed look done or skipped', () => {
    const missed = task({ missed: true });
    expect(missed.done).toBe(false);
    expect(missed.skipped).toBe(false);
  });

  it('leaves overdue tasks open', () => {
    expect(isClosed(task({ overdue: true }))).toBe(false);
  });

  it('keeps done and skipped closed', () => {
    expect(isClosed(task({ done: true }))).toBe(true);
    expect(isClosed(task({ skipped: true }))).toBe(true);
    expect(isClosed(task({}))).toBe(false);
  });
});

describe('isBacklog', () => {
  it('reads the explicit flag and leaves the task open', () => {
    const item = task({ backlog: true, dueDate: null });
    expect(isBacklog(item)).toBe(true);
    expect(isClosed(item)).toBe(false);
    expect(isOverdue(item, '2026-10-27')).toBe(false);
  });

  it('does not infer backlog from a missing date', () => {
    expect(isBacklog(task({ dueDate: null }))).toBe(false);
  });
});

describe('isOverdue', () => {
  it('accepts the backend flag', () => {
    expect(isOverdue(task({ overdue: true }), '2026-10-27')).toBe(true);
  });

  it('falls back to the scheduled date for legacy rows', () => {
    expect(isOverdue(task({ dueDate: '2026-10-26' }), '2026-10-27')).toBe(true);
    expect(isOverdue(task({ dueDate: '2026-10-27' }), '2026-10-27')).toBe(false);
  });

  it('never flags a closed task', () => {
    const today = '2026-10-27';
    expect(isOverdue(task({ dueDate: '2026-10-20', done: true }), today)).toBe(false);
    expect(isOverdue(task({ dueDate: '2026-10-20', missed: true }), today)).toBe(false);
  });
});
