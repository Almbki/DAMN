import { apiPollJob, apiRequest, apiStream, apiUpload, isApiError } from '@/api/client';
import { apiPrefix } from '@/api/config';
import { deleteTaskQuery, type DeleteTaskOptions } from '@/api/delete-task-query';
import type {
  ConfirmPlanResponse,
  FeedbackCreate,
  FeedbackObligationRead,
  FeedbackRead,
  FeedbackSubmitResponse,
  GoalCreateRequest,
  GoalDetailRead,
  GoalLifecycleImpact,
  GoalSetArchiveImpact,
  GoalSetAttachResponse,
  GoalSetCreateRequest,
  GoalSetDetailRead,
  GoalSetRead,
  GoalSetRestoreImpact,
  GoalSetUpdateRequest,
  GoalStatus,
  InsightRead,
  JobAccepted,
  JobStatus,
  ModelRuntimeRead,
  PlanChangeRead,
  PlanGenerateRequest,
  PlanListItem,
  PlanRead,
  PreviewResponse,
  ProfileRead,
  ProfileUpdateRequest,
  RegisterRequest,
  ReplanEligibilityRead,
  ReplanRequest,
  ScheduleEventRead,
  ScheduleImportResult,
  SchedulingPreferences,
  SituationTrendRead,
  SyntheticImportSummary,
  SyntheticResetSummary,
  SyntheticScenarioList,
  SyntheticStatus,
  TaskMoveRequest,
  TaskRead,
  TaskUpdateRequest,
  TokenResponse,
  TraitAssessmentRead,
  TraitReassessmentEligibilityRead,
  UpdateGoalRequest,
  UserRead,
} from '@/api/types';

/** Minimal handle needed to stream/poll an async generation job. */
export type JobHandle = {
  job_id: string;
  events_url: string;
  status_url: string;
};

export function register(body: RegisterRequest) {
  return apiRequest<UserRead>('/auth/register', { method: 'POST', body, auth: false });
}

export function login(email: string, password: string) {
  return apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  });
}

export function getMe() {
  return apiRequest<UserRead>('/users/me');
}

export function updateMe(body: { display_name?: string; execution_weight?: number }) {
  return apiRequest<UserRead>('/users/me', { method: 'PATCH', body });
}

/**
 * 基础画像 + adaptive state (flat `ProfileRead`); the caller treats a 404 as
 * "no profile yet".
 */
export function getMyProfile() {
  return apiRequest<ProfileRead>('/users/me/profile');
}

/** Sending any field re-initialises the backend state from the new profile. */
export function updateMyProfile(body: ProfileUpdateRequest) {
  return apiRequest<UserRead>('/users/me', { method: 'PATCH', body });
}

/** Scheduling preferences in effect (`GET /users/me/preferences`). */
export function getPreferences() {
  return apiRequest<SchedulingPreferences>('/users/me/preferences');
}

/** Full overwrite of the scheduling preferences (`PUT /users/me/preferences`). */
export function putPreferences(body: SchedulingPreferences) {
  // `apiRequest`'s RequestOptions method union predates PUT; the runtime is fine.
  return apiRequest<SchedulingPreferences>('/users/me/preferences', {
    method: 'PUT' as unknown as 'POST',
    body,
  });
}

/** Energy / stress / efficacy trend for the profile page. */
export function getSituationTrends(days = 14) {
  return apiRequest<SituationTrendRead>(`/users/me/situation/trends?days=${days}`);
}

/** Developer/debug: model versions, artifact hashes and Level 3 shadow summary. */
export function getModelRuntime() {
  return apiRequest<ModelRuntimeRead>('/users/me/model-runtime');
}

/** Start (or resume) the Level 1 CAT assessment. Idempotent. */
export function startTraitAssessment(restart = false) {
  const query = restart ? '?restart=true' : '';
  return apiRequest<TraitAssessmentRead>(`/users/me/trait-assessment/start${query}`, {
    method: 'POST',
  });
}

export function getTraitAssessment(assessmentId: string) {
  return apiRequest<TraitAssessmentRead>(`/users/me/trait-assessment/${assessmentId}`);
}

export function answerTraitAssessment(assessmentId: string, itemId: string, response: number) {
  return apiRequest<TraitAssessmentRead>(
    `/users/me/trait-assessment/${assessmentId}/answer`,
    { method: 'POST', body: { item_id: itemId, response } },
  );
}

export function getReassessmentEligibility() {
  return apiRequest<TraitReassessmentEligibilityRead>(
    '/users/me/trait-assessment/reassessment-eligibility',
  );
}

// --- developer / synthetic scenarios (feature-flagged backend) -------------
export function listSyntheticScenarios() {
  return apiRequest<SyntheticScenarioList>('/dev/scenarios');
}

export function getSyntheticStatus() {
  return apiRequest<SyntheticStatus>('/dev/scenarios/status');
}

export function importSyntheticScenario(scenarioName: string) {
  return apiRequest<SyntheticImportSummary>('/dev/scenarios/import', {
    method: 'POST',
    body: { scenario_name: scenarioName },
  });
}

export function resetSyntheticData() {
  return apiRequest<SyntheticResetSummary>('/dev/scenarios/reset', { method: 'POST' });
}

/** List goals; pass `status='draft'` for the 待拆解清单. */
export function listGoals(
  status?: GoalStatus,
  opts: { includeArchived?: boolean } = {},
) {
  const params: string[] = [];
  if (status) params.push(`status=${encodeURIComponent(status)}`);
  if (opts.includeArchived === false) params.push('include_archived=false');
  const query = params.length > 0 ? `?${params.join('&')}` : '';
  return apiRequest<GoalDetailRead[]>(`/goals${query}`);
}

/** Create a goal (or a draft item with `status: 'draft'`). */
export function createGoal(body: GoalCreateRequest) {
  return apiRequest<GoalDetailRead>('/goals', { method: 'POST', body });
}

/** Edit a goal (title / description / status / deadline / priority). */
export function updateGoal(goalId: number, body: UpdateGoalRequest) {
  return apiRequest<GoalDetailRead>(`/goals/${goalId}`, { method: 'PATCH', body });
}

/** Delete a goal (204 on success). */
export function deleteGoal(goalId: number) {
  return apiRequest<void>(`/goals/${goalId}`, { method: 'DELETE' });
}

/** Archive one goal: it stops feeding new plans, history is preserved. */
export function archiveGoal(goalId: number) {
  return apiRequest<GoalLifecycleImpact>(`/goals/${goalId}/archive`, { method: 'POST' });
}

/** Restore one archived goal. */
export function restoreGoal(goalId: number) {
  return apiRequest<GoalLifecycleImpact>(`/goals/${goalId}/restore`, { method: 'POST' });
}

// --- goal sets (目标集) ---------------------------------------------------

/** Goal sets, newest first; archived ones are included only when asked for. */
export function listGoalSets(includeArchived = true) {
  const query = includeArchived ? '?include_archived=true' : '';
  return apiRequest<GoalSetRead[]>(`/goal-sets${query}`);
}

export function createGoalSet(body: GoalSetCreateRequest) {
  return apiRequest<GoalSetRead>('/goal-sets', { method: 'POST', body });
}

export function getGoalSet(goalSetId: number) {
  return apiRequest<GoalSetDetailRead>(`/goal-sets/${goalSetId}`);
}

export function updateGoalSet(goalSetId: number, body: GoalSetUpdateRequest) {
  return apiRequest<GoalSetRead>(`/goal-sets/${goalSetId}`, { method: 'PATCH', body });
}

/** Archive the whole set; the response reports what was removed/preserved. */
export function archiveGoalSet(goalSetId: number) {
  return apiRequest<GoalSetArchiveImpact>(`/goal-sets/${goalSetId}/archive`, {
    method: 'POST',
  });
}

export function restoreGoalSet(goalSetId: number) {
  return apiRequest<GoalSetRestoreImpact>(`/goal-sets/${goalSetId}/restore`, {
    method: 'POST',
  });
}

/** Attach existing goals to a set (`POST /goal-sets/{id}/goals`). */
export function attachGoalsToSet(goalSetId: number, goalIds: number[]) {
  return apiRequest<GoalSetAttachResponse>(`/goal-sets/${goalSetId}/goals`, {
    method: 'POST',
    body: { goal_ids: goalIds },
  });
}

export function listPlans() {
  return apiRequest<PlanListItem[]>('/plans');
}

export function getPlan(planId: number) {
  return apiRequest<PlanRead>(`/plans/${planId}`);
}

/** What the system changed, day by day, for this plan version. */
export function getPlanChanges(planId: number) {
  return apiRequest<PlanChangeRead[]>(`/plans/${planId}/changes`);
}

/** 落库：草稿 → 正式计划（`POST /plans/preview/{thread_id}/confirm`）。 */
export function confirmPreview(threadId: string) {
  return apiRequest<ConfirmPlanResponse>(`/plans/preview/${threadId}/confirm`, { method: 'POST' });
}

/** Cross-device recovery: current user's latest completed preview, if any. */
export function getLatestPreview() {
  return apiRequest<PreviewResponse>('/plans/preview/latest');
}

export function listFeedback(planId: number) {
  return apiRequest<FeedbackRead[]>(`/plans/${planId}/feedback`);
}

/** Unresolved feedback debts for the signed-in user, oldest day first. */
export function listFeedbackObligations() {
  return apiRequest<FeedbackObligationRead[]>('/feedback/obligations');
}

export function patchTask(planId: number, taskId: number, body: TaskUpdateRequest) {
  return apiRequest<TaskRead>(`/plans/${planId}/tasks/${taskId}`, { method: 'PATCH', body });
}

/** Deterministic drag MOVE; the backend snaps the start to 30 minutes. */
export function moveTask(
  planId: number,
  taskId: number,
  targetDate: string,
  targetStart: string,
) {
  const body: TaskMoveRequest = {
    target_date: targetDate,
    target_start: targetStart,
  };
  return apiRequest<TaskRead>(`/plans/${planId}/tasks/${taskId}/move`, {
    method: 'POST',
    body,
  });
}

/** Move a task into the explicit 任务池 (idempotent). */
export function moveTaskToBacklog(planId: number, taskId: number) {
  return apiRequest<TaskRead>(`/plans/${planId}/tasks/${taskId}/backlog`, {
    method: 'POST',
  });
}

/** Atomically shift this task and its later unfinished siblings. */
export function localReschedule(planId: number, taskId: number) {
  return apiRequest<TaskRead[]>(`/plans/${planId}/tasks/${taskId}/local-reschedule`, {
    method: 'POST',
  });
}

/** Backend-authoritative 任务池 list (`status=backlog` only). */
export function listBacklog(planId: number) {
  return apiRequest<TaskRead[]>(`/plans/${planId}/backlog`);
}

/**
 * Soft-delete a task (204 on success, idempotent). `scope=series` removes the
 * unfinished occurrences of a repeating series in this plan only.
 */
export function deleteTask(
  planId: number,
  taskId: number,
  options: DeleteTaskOptions = {},
) {
  return apiRequest<void>(
    `/plans/${planId}/tasks/${taskId}${deleteTaskQuery(options)}`,
    { method: 'DELETE' },
  );
}

/**
 * `opts.streamReplan` defers the replan graph to an async job; the response then
 * carries `replan_job_id` and the caller drives it with `runJob`.
 */
export function submitFeedback(
  planId: number,
  body: FeedbackCreate,
  opts: { streamReplan?: boolean } = {},
) {
  const query = opts.streamReplan ? '?stream_replan=true' : '';
  return apiRequest<FeedbackSubmitResponse>(`/plans/${planId}/feedback${query}`, {
    method: 'POST',
    body,
  });
}

export function getInsights(planId: number) {
  return apiRequest<InsightRead>(`/plans/${planId}/insights`);
}

export function replanEligibility(planId: number) {
  return apiRequest<ReplanEligibilityRead>(`/plans/${planId}/replan/eligibility`);
}

export function replan(planId: number, body: ReplanRequest) {
  // 202 + job handle; the `ReplanResponse` lives in the job result.
  return apiRequest<JobAccepted>(`/plans/${planId}/replan`, { method: 'POST', body });
}

// --- schedule / timetable ------------------------------------------------

/**
 * A picked file ready for upload. Web passes the DOM `File`; native passes a
 * `Blob` read from the cached URI (so `expo/fetch` can serialise it).
 */
export type ScheduleUploadFile = {
  uri: string;
  name: string;
  mimeType?: string | null;
  file?: Blob | null;
};

/** Events that can occur inside `[from, to]` (weekly recurrences included). */
export function listSchedules(from: string, to: string) {
  const query = `from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;
  return apiRequest<ScheduleEventRead[]>(`/schedules?${query}`);
}

/**
 * Upload a CSV/XLSX timetable. The backend parses the file, so the client only
 * has to attach it; `dry_run` validates without storing.
 */
export function importSchedules(
  file: ScheduleUploadFile,
  opts: { dryRun?: boolean } = {},
) {
  const form = new FormData();
  if (file.file) {
    form.append('file', file.file, file.name);
  } else {
    // Last-resort React Native descriptor. The normal native path supplies a
    // Blob (see `ScheduleUploadFile.file`), but keep this so a caller that only
    // has a URI still produces a valid multipart part on RN.
    form.append('file', {
      uri: file.uri,
      name: file.name,
      type: file.mimeType ?? 'application/octet-stream',
    } as unknown as Blob);
  }
  const query = opts.dryRun ? '?dry_run=true' : '';
  return apiUpload<ScheduleImportResult>(`/schedules/import${query}`, form);
}

/** Soft-delete an imported event (`204` on success). */
export function deleteSchedule(id: number) {
  return apiRequest<void>(`/schedules/${id}`, { method: 'DELETE' });
}

// --- async generation jobs (stream first, poll as fallback) ----------------

/** Enqueue a preview generation; resolve via `runJob`. */
export function submitPreview(body: PlanGenerateRequest) {
  return apiRequest<JobAccepted>('/plans/preview', { method: 'POST', body });
}

/** Enqueue a bounded preview adjustment; resolve via `runJob`. */
export function submitAdjustPreview(threadId: string, feedback: string) {
  return apiRequest<JobAccepted>(`/plans/preview/${threadId}/adjust`, {
    method: 'POST',
    body: { feedback },
  });
}

/** Errors that mean "the stream cannot carry this", so polling is safe. */
const FALLBACK_CODES = new Set([
  'no_stream',
  'network_error',
  'stream_error',
  'stream_timeout',
]);

/**
 * Backend URLs are rooted at `/api/v1` while `apiRequest`/`apiStream` add the
 * prefix themselves. Normalise an absolute or prefixed URL back to a path.
 */
function toApiPath(url: string | null | undefined): string {
  if (!url) return '';
  const withoutOrigin = url.replace(/^[a-z]+:\/\/[^/]+/i, '');
  const path = withoutOrigin.startsWith(apiPrefix)
    ? withoutOrigin.slice(apiPrefix.length)
    : withoutOrigin;
  if (!path) return '/';
  return path.startsWith('/') ? path : `/${path}`;
}

/** Build a job handle when only the feedback response's `replan_job_id` is known. */
export function jobHandleFromId(jobId: string): JobHandle {
  const base = `/plans/generation/${jobId}`;
  return { job_id: jobId, events_url: `${base}/events`, status_url: base };
}

/**
 * Drive a job to completion: stream its SSE stages, then read the final status.
 * Falls back to polling when streaming is unavailable or the stream breaks.
 * Returns the finished `JobStatus` (its `result` holds the payload).
 */
export async function runJob(
  job: JobHandle,
  onStage?: (stage: string, data: any) => void,
  signal?: AbortSignal,
): Promise<JobStatus> {
  const fallbackBase = `/plans/generation/${job.job_id}`;
  const eventsPath = toApiPath(job.events_url) || `${fallbackBase}/events`;
  const statusPath = toApiPath(job.status_url) || fallbackBase;
  try {
    await apiStream(eventsPath, { onStage: onStage ?? (() => undefined) }, signal);
  } catch (error) {
    // Re-throw real failures (401/404/aborted); only recover from stream gaps.
    if (!(isApiError(error) && FALLBACK_CODES.has(error.code))) throw error;
  }
  // ALWAYS resolve on a terminal status: the stream can end before the worker
  // finishes (platform buffering, proxy, early close), and returning a
  // still-`running` status makes every caller read `result.thread_id` off null.
  // `apiPollJob` returns immediately when the job is already terminal.
  return apiPollJob(statusPath, { signal });
}
