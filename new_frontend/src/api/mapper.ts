import { hhmm } from '@/api/format';
import type {
  GoalDetailRead,
  PlanChangeRead,
  PreviewTaskRead,
  SituationTrendRead,
  TaskRead,
  TaskUpdateRequest,
} from '@/api/types';
import { todayISO } from '@/domain/date';
import type { DraftTask, PendingTask } from '@/domain/decompose';
import type { PlanChange } from '@/domain/plan-change';
import type { Situation, SituationPoint } from '@/domain/situation';
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

export function previewToDrafts(tasks: PreviewTaskRead[]): DraftTask[] {
  return tasks.map((task, index) => ({
    id: index + 1,
    // Preview tasks carry the persisted `goal_id`, not the pending-list index.
    sourceId: task.goal_id ?? 0,
    title: task.title,
    dueDate: task.scheduled_date ? task.scheduled_date.slice(0, 10) : todayISO(),
    startTime: task.start_time ? hhmm(task.start_time) : '09:00',
    endTime: task.end_time ? hhmm(task.end_time) : '09:30',
    estimatedMinutes: task.estimated_duration,
    priority: Math.min(3, Math.max(1, task.priority || 2)),
  }));
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

/** Backend `GoalDetailRead` → the 待拆解 `PendingTask` the goal screen edits. */
export function pendingTaskFromGoal(goal: GoalDetailRead): PendingTask {
  return {
    id: goal.id,
    title: goal.title,
    priority: Math.min(3, Math.max(1, goal.priority || 2)),
    dueDate: goal.deadline ? goal.deadline.slice(0, 10) : null,
    notes: goal.description ?? '',
  };
}

/**
 * Backend `PlanChangeRead` (snake_case, one entry per replan) → the app's
 * `PlanChange` notice shape. The backend's per-day `task_ids` are dropped: the
 * notice only reads the counts + summary.
 */
export function planChangeFromApi(raw: PlanChangeRead): PlanChange {
  return {
    id: raw.id,
    triggerType: raw.trigger_type,
    reason: raw.reason,
    oldVersion: raw.old_version,
    newVersion: raw.new_version,
    createdAt: raw.created_at,
    days: raw.days.map((day) => ({
      date: day.date,
      added: day.added,
      moved: day.moved,
      removed: day.removed,
      summary: day.summary,
    })),
  };
}

/**
 * `SituationTrendRead` → the profile's `Situation`. The latest point carries the
 * headline numbers; `drivers` become the "why" lines. Mock mode still derives
 * its value with `buildSituation` from local feedback.
 */
export function situationFromTrends(raw: SituationTrendRead): Situation {
  const points: SituationPoint[] = raw.points.map((point) => ({
    date: point.date,
    energy: point.energy,
    stress: point.stress,
    efficacy: point.efficacy,
  }));
  const latest = points.length > 0 ? points[points.length - 1] : null;
  const lastEfficacy = [...points].reverse().find((point) => point.efficacy != null)?.efficacy;
  return {
    energy: latest?.energy ?? null,
    stress: latest?.stress ?? null,
    efficacy: lastEfficacy ?? 0,
    points,
    samples: raw.samples,
    minSamples: raw.min_samples,
    sufficient: raw.sufficient,
    reasons: raw.drivers,
  };
}
