import { describe, expect, it } from 'vitest';

import {
  isRecurringSeriesTask,
  seriesTasks,
  type Task,
} from '@/domain/task';

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

describe('isRecurringSeriesTask', () => {
  it('recognises a backend series id', () => {
    expect(isRecurringSeriesTask(task({ seriesId: 'series-a' }))).toBe(true);
  });

  it('recognises legacy non-one-off kinds', () => {
    expect(isRecurringSeriesTask(task({ taskKind: 'routine' }))).toBe(true);
    expect(isRecurringSeriesTask(task({ taskKind: 'long_term' }))).toBe(true);
    expect(isRecurringSeriesTask(task({ taskKind: 'one_off' }))).toBe(false);
  });
});

describe('seriesTasks', () => {
  it('groups occurrences by series id', () => {
    const tasks = [
      task({ id: 1, seriesId: 'a' }),
      task({ id: 2, seriesId: 'a' }),
      task({ id: 3, seriesId: 'b' }),
    ];
    expect(seriesTasks(tasks, tasks[0]).map((item) => item.id)).toEqual([1, 2]);
  });

  it('resolves a one-off task to itself', () => {
    const tasks = [
      task({ id: 1 }),
      task({ id: 2, goalId: 9, taskKind: 'routine', seriesId: null }),
    ];
    expect(seriesTasks(tasks, tasks[0]).map((item) => item.id)).toEqual([1]);
  });

  it('falls back to goal + task kind when a legacy series has no id', () => {
    const tasks = [
      task({ id: 1, goalId: 9, taskKind: 'routine', seriesId: null }),
      task({ id: 2, goalId: 9, taskKind: 'routine', seriesId: null }),
      task({ id: 3, goalId: 9, taskKind: 'long_term', seriesId: null }),
      task({ id: 4, goalId: 10, taskKind: 'routine', seriesId: null }),
    ];
    expect(seriesTasks(tasks, tasks[0]).map((item) => item.id)).toEqual([1, 2]);
  });
});
