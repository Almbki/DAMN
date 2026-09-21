import { hhmm } from '@/api/format';
import type { TaskRead, TaskUpdateRequest } from '@/api/types';
import { NO_REPEAT, type CognitiveLoad, type Task } from '@/domain/task';

function mapCognitiveLoad(value: string): CognitiveLoad {
  if (value === 'high') return 'high';
  if (value === 'low' || value === 'restorative') return 'low';
  return 'medium';
}

/**
 * Backend `TaskRead` → local `Task`.
 *
 * Fields the backend does not store (notes, repeat, tags, actualMinutes,
 * completedAt) default to empty. `scheduled_date` is the day; `start_time` is
 * also used as the due time since the UI only shows one time.
 */
export function taskFromApi(raw: TaskRead): Task {
  return {
    id: raw.id,
    title: raw.title,
    description: raw.description ?? '',
    notes: '',
    goalId: raw.goal_id ?? null,
    priority: Math.min(3, Math.max(1, raw.priority || 2)),
    done: raw.status === 'completed',
    skipped: raw.status === 'skipped',
    startDate: null,
    startTime: raw.start_time ? hhmm(raw.start_time) : null,
    dueDate: raw.scheduled_date ? raw.scheduled_date.slice(0, 10) : null,
    dueTime: raw.start_time ? hhmm(raw.start_time) : null,
    endTime: raw.end_time ? hhmm(raw.end_time) : null,
    estimatedMinutes: raw.estimated_duration ?? null,
    actualMinutes: null,
    cognitiveLoad: mapCognitiveLoad(raw.cognitive_load),
    repeat: NO_REPEAT,
    tags: [],
    order: raw.order_index ?? 0,
    completedAt: null,
  };
}

/**
 * Un-completing must go through `status`: the backend's `update_task` only acts
 * on `completed: true`, so `{ completed: false }` is a silent no-op there.
 */
export function patchDone(done: boolean): TaskUpdateRequest {
  return done ? { completed: true } : { status: 'scheduled' };
}

export function patchSkipped(): TaskUpdateRequest {
  return { status: 'skipped' };
}
