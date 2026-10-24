import { describe, expect, it } from 'vitest';

import {
  patchDone,
  taskCompletePatch,
  taskFromApi,
  taskPartialPatch,
} from '@/api/mapper';
import type { TaskRead } from '@/api/types';

const base = {
  id: 1,
  plan_id: 1,
  goal_id: null,
  parent_task_id: null,
  title: 'Task',
  description: null,
  estimated_duration: 60,
  predicted_duration: 60,
  cognitive_load: 'medium',
  priority: 2,
  scheduled_date: '2026-10-24',
  start_time: '09:00:00',
  end_time: '10:00:00',
  status: 'scheduled',
  completion_probability: null,
  prediction_source: 'deterministic:workload_estimate',
  prediction_mode: 'production',
  is_flexible: true,
  task_kind: 'one_off',
  series_id: null,
  series_index: null,
  occurrence_date: null,
  target_amount: null,
  target_unit: null,
  order_index: 0,
  standards: [],
} as TaskRead;

describe('task mapper', () => {
  it('preserves a null completion probability (no fake 0%)', () => {
    const task = taskFromApi({ ...base, completion_probability: null });
    expect(task.completionProbability).toBeNull();
  });

  it('maps production provenance fields', () => {
    const task = taskFromApi(base);
    expect(task.predictionSource).toBe('deterministic:workload_estimate');
    expect(task.predictionMode).toBe('production');
    expect(task.startedAt).toBeNull();
  });

  it('maps the active execution start so a refresh can show in-progress', () => {
    const task = taskFromApi({
      ...base,
      started_at: '2026-10-24T09:15:00.000Z',
    });
    expect(task.startedAt).toBe('2026-10-24T09:15:00.000Z');
  });

  it('keeps a real completion probability untouched', () => {
    const task = taskFromApi({ ...base, completion_probability: 0.42 });
    expect(task.completionProbability).toBeCloseTo(0.42);
  });
});

describe('execution patches', () => {
  it('completes with an actual duration and timestamp', () => {
    const body = taskCompletePatch(90.4, 2, new Date('2026-10-24T10:00:00Z'));
    expect(body.completed).toBe(true);
    expect(body.actual_duration).toBe(90);
    expect(body.interruption_count).toBe(2);
    expect(body.finished_at).toBe('2026-10-24T10:00:00.000Z');
  });

  it('saves partial completion clamped to 0..1', () => {
    expect(taskPartialPatch(0.5, 30).completion_rate).toBe(0.5);
    expect(taskPartialPatch(1.4).completion_rate).toBe(1);
    expect(taskPartialPatch(-0.2).completion_rate).toBe(0);
    expect(taskPartialPatch(0.5, 30).completed).toBe(false);
  });

  it('preserves observed zero interruptions and omits missing ones', () => {
    expect(taskPartialPatch(0.5, 30, 0).interruption_count).toBe(0);
    expect(taskPartialPatch(0.5, 30, 3).interruption_count).toBe(3);
    expect(taskPartialPatch(0.5, 30).interruption_count).toBeUndefined();
    expect(taskCompletePatch(30, 0).interruption_count).toBe(0);
  });

  it('un-completing uses status, completing records a finish time', () => {
    expect(patchDone(false)).toEqual({ status: 'scheduled' });
    expect(patchDone(true).completed).toBe(true);
    expect(patchDone(true).finished_at).toBeTruthy();
  });
});