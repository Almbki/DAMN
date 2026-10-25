import { hhmm } from '@/api/format';
import type {
  EstimateAccuracyDay,
  EstimateAccuracyResponse,
  EstimateAccuracySummary,
  GoalDetailRead,
  GoalRead,
  PlanChangeRead,
  PreviewTaskRead,
  SituationTrendRead,
  TaskRead,
  TaskUpdateRequest,
} from '@/api/types';
import { todayISO } from '@/domain/date';
import type { DraftTask, PendingTask } from '@/domain/decompose';
import type { Goal, GoalStatus } from '@/domain/goal';
import type { PlanChange } from '@/domain/plan-change';
import type { Situation, SituationPoint } from '@/domain/situation';
import {
  NO_REPEAT,
  type CognitiveLoad,
  type Task,
  type TaskStandard,
} from '@/domain/task';

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
  const standards: TaskStandard[] = (raw.standards ?? []).map((standard) => ({
    id: standard.id,
    description: standard.description,
    estimatedDuration: standard.estimated_duration,
    completed: standard.completed,
    orderIndex: standard.order_index,
  }));
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
    taskKind: raw.task_kind ?? 'one_off',
    seriesId: raw.series_id ?? null,
    seriesIndex: raw.series_index ?? null,
    occurrenceDate: raw.occurrence_date ? raw.occurrence_date.slice(0, 10) : null,
    targetAmount: raw.target_amount ?? null,
    targetUnit: raw.target_unit ?? null,
    tags: [],
    order: raw.order_index ?? 0,
    completedAt: null,
    standards,
    completionProbability: raw.completion_probability ?? null,
    predictedDuration: raw.predicted_duration ?? null,
    predictionSource: raw.prediction_source ?? null,
    predictionMode: raw.prediction_mode ?? null,
    startedAt: raw.started_at ?? null,
    isFlexible: raw.is_flexible,
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
    taskKind: task.task_kind ?? 'one_off',
    seriesId: task.series_id ?? null,
    seriesIndex: task.series_index ?? null,
    occurrenceDate: task.occurrence_date ? task.occurrence_date.slice(0, 10) : null,
    targetAmount: task.target_amount ?? null,
    targetUnit: task.target_unit ?? null,
  }));
}

/**
 * Un-completing must go through `status`: the backend's `update_task` only acts
 * on `completed: true`, so `{ completed: false }` is a silent no-op there.
 */
export function patchDone(done: boolean): TaskUpdateRequest {
  return done
    ? { completed: true, finished_at: new Date().toISOString() }
    : { status: 'scheduled' };
}

/** Execution capture: start a task (backend records a partial TaskExecution). */
export function taskStartPatch(now = new Date()): TaskUpdateRequest {
  return { started_at: now.toISOString() };
}

/** Execution capture: complete a task with a best-effort actual duration. */
export function taskCompletePatch(
  actualMinutes?: number | null,
  interruptionCount?: number | null,
  now = new Date(),
): TaskUpdateRequest {
  const body: TaskUpdateRequest = {
    completed: true,
    finished_at: now.toISOString(),
  };
  if (actualMinutes != null && Number.isFinite(actualMinutes) && actualMinutes > 0) {
    body.actual_duration = Math.round(actualMinutes);
  }
  if (interruptionCount != null) {
    body.interruption_count = Math.max(0, Math.round(interruptionCount));
  }
  return body;
}

/** Execution capture: partial completion (0..1) + actual duration. */
export function taskPartialPatch(
  completionRate: number,
  actualMinutes?: number | null,
  interruptionCount?: number | null,
  now = new Date(),
): TaskUpdateRequest {
  const body: TaskUpdateRequest = {
    completed: false,
    completion_rate: Math.min(1, Math.max(0, completionRate)),
    finished_at: now.toISOString(),
  };
  if (actualMinutes != null && Number.isFinite(actualMinutes) && actualMinutes > 0) {
    body.actual_duration = Math.round(actualMinutes);
  }
  if (interruptionCount != null) {
    body.interruption_count = Math.max(0, Math.round(interruptionCount));
  }
  return body;
}

export function patchSkipped(): TaskUpdateRequest {
  return { status: 'skipped' };
}

/**
 * Domain `Partial<Task>` → backend `TaskUpdateRequest`.
 *
 * Only the fields the backend exposes are forwarded; local-only concepts
 * (`repeat`, `tags`, `startDate`, …) are ignored rather than sent blindly.
 */
export function taskPatchFromDomain(patch: Partial<Task>): TaskUpdateRequest {
  const body: TaskUpdateRequest = {};

  if (patch.title !== undefined) body.title = patch.title.trim() || '未命名任务';
  if (patch.description !== undefined) body.description = patch.description;
  else if (patch.notes !== undefined) body.description = patch.notes;
  if (patch.estimatedMinutes !== undefined && patch.estimatedMinutes != null) {
    body.estimated_duration = patch.estimatedMinutes;
  }
  if (patch.priority !== undefined) {
    body.priority = Math.min(4, Math.max(1, Math.round(patch.priority)));
  }
  if (patch.cognitiveLoad !== undefined) body.cognitive_load = patch.cognitiveLoad;
  if (patch.dueDate !== undefined) body.scheduled_date = patch.dueDate;
  if (patch.startTime !== undefined) body.start_time = patch.startTime;
  else if (patch.dueTime !== undefined) body.start_time = patch.dueTime;
  if (patch.endTime !== undefined) body.end_time = patch.endTime;

  if (patch.done !== undefined) Object.assign(body, patchDone(patch.done));
  if (patch.skipped !== undefined) Object.assign(body, patchSkipped());

  return body;
}

/** Backend `GoalDetailRead` → the 待拆解 `PendingTask` the goal screen edits. */
export function pendingTaskFromGoal(goal: GoalDetailRead): PendingTask {
  return {
    id: goal.id,
    title: goal.title,
    priority: Math.min(3, Math.max(1, goal.priority || 2)),
    dueDate: goal.deadline ? goal.deadline.slice(0, 10) : null,
    notes: goal.description ?? '',
    taskKind: goal.task_kind ?? 'one_off',
    startDate: goal.start_date ? goal.start_date.slice(0, 10) : null,
    dailyTargetMinutes: goal.daily_target_minutes ?? null,
    recurrenceWeekdays: goal.recurrence_weekdays ?? null,
    targetAmount: goal.target_amount ?? null,
    targetUnit: goal.target_unit ?? null,
  };
}

function mapGoalStatus(status: string): GoalStatus {
  if (status === 'completed' || status === 'archived' || status === 'cancelled' || status === 'draft') {
    return status;
  }
  return 'active';
}

/** Backend `GoalRead` (plan payload) → the app's `Goal` group label. */
export function goalFromApi(raw: GoalRead): Goal {
  return {
    id: raw.id,
    title: raw.title,
    description: raw.description ?? '',
    status: mapGoalStatus(raw.status),
    deadline: raw.deadline ? raw.deadline.slice(0, 10) : null,
    estimatedMinutes: raw.estimated_minutes ?? null,
    priority: Math.min(3, Math.max(1, raw.priority ?? 2)),
    createdAt: '',
    taskKind: raw.task_kind ?? 'one_off',
    startDate: raw.start_date ? raw.start_date.slice(0, 10) : null,
    dailyTargetMinutes: raw.daily_target_minutes ?? null,
    recurrenceWeekdays: raw.recurrence_weekdays ?? null,
    targetAmount: raw.target_amount ?? null,
    targetUnit: raw.target_unit ?? null,
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
      taskIds: day.task_ids,
    })),
  };
}

/**
 * `SituationTrendRead` → the profile's `Situation`. The latest point carries the
 * headline numbers; `drivers` become the "why" lines. Mock mode still derives
 * its value with `buildSituation` from local feedback.
 */
/** Coerce a per-day estimate row; `null` when it has no usable date. */
function estimateDayFromApi(raw: Partial<EstimateAccuracyDay>): EstimateAccuracyDay | null {
  const date = typeof raw.date === 'string' ? raw.date.slice(0, 10) : '';
  if (!date) return null;
  const plannedRaw = typeof raw.planned_minutes === 'number' ? raw.planned_minutes : 0;
  const actualRaw = typeof raw.actual_minutes === 'number' ? raw.actual_minutes : 0;
  const planned = Math.max(0, Math.round(plannedRaw));
  const actual = Math.max(0, Math.round(actualRaw));
  const ratio =
    typeof raw.ratio === 'number' && Number.isFinite(raw.ratio)
      ? raw.ratio
      : planned > 0
        ? Math.round((actual / planned) * 100) / 100
        : null;
  return { date, planned_minutes: planned, actual_minutes: actual, ratio };
}

/**
 * Normalise GET /users/me/estimate-accuracy. Accepts the bare per-day list and
 * the wrapped object (`points`/`daily`/`days` + totals) so either backend
 * envelope renders. Returns `null` when there is nothing to show.
 */
export function estimateAccuracyFromApi(
  raw: EstimateAccuracyResponse | EstimateAccuracyDay[] | null | undefined,
): EstimateAccuracySummary | null {
  if (raw == null) return null;

  const entries: Partial<EstimateAccuracyDay>[] = Array.isArray(raw)
    ? raw
    : (raw.points ?? raw.daily ?? (Array.isArray(raw.days) ? raw.days : []));
  const points = entries
    .map(estimateDayFromApi)
    .filter((point): point is EstimateAccuracyDay => point != null)
    .sort((a, b) => a.date.localeCompare(b.date));

  const explicitPlanned = Array.isArray(raw)
    ? null
    : (raw.planned_minutes ?? raw.total_planned_minutes);
  const explicitActual = Array.isArray(raw)
    ? null
    : (raw.actual_minutes ?? raw.total_actual_minutes);
  const planned =
    typeof explicitPlanned === 'number'
      ? explicitPlanned
      : points.reduce((sum, point) => sum + point.planned_minutes, 0);
  const actual =
    typeof explicitActual === 'number'
      ? explicitActual
      : points.reduce((sum, point) => sum + point.actual_minutes, 0);
  const rawRatio = Array.isArray(raw) ? null : raw.ratio;
  const ratio =
    typeof rawRatio === 'number' && Number.isFinite(rawRatio)
      ? rawRatio
      : planned > 0
        ? Math.round((actual / planned) * 100) / 100
        : null;

  if (points.length === 0 && planned === 0 && actual === 0) return null;
  return { points, planned_minutes: planned, actual_minutes: actual, ratio };
}

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
