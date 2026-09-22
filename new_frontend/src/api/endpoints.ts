import { apiPollJob, apiRequest, apiStream, isApiError } from '@/api/client';
import type {
  ConfirmPlanResponse,
  FeedbackCreate,
  FeedbackRead,
  FeedbackSubmitResponse,
  GoalCreateRequest,
  GoalDetailRead,
  GoalStatus,
  InsightRead,
  JobAccepted,
  JobStatus,
  PlanChangeRead,
  PlanGenerateRequest,
  PlanGenerateResponse,
  PlanListItem,
  PlanRead,
  ProfileRead,
  ProfileUpdateRequest,
  RegisterRequest,
  ReplanEligibilityRead,
  ReplanRequest,
  ReplanResponse,
  SchedulingPreferences,
  SituationTrendRead,
  TaskRead,
  TaskUpdateRequest,
  TokenResponse,
  UpdateGoalRequest,
  UserRead,
} from '@/api/types';

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

/** List goals; pass `status='draft'` for the 待拆解清单. */
export function listGoals(status?: GoalStatus) {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
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

export function generatePlan(body: PlanGenerateRequest) {
  return apiRequest<PlanGenerateResponse>('/plans/generate', { method: 'POST', body });
}

/** 落库：草稿 → 正式计划（`POST /plans/preview/{thread_id}/confirm`）。 */
export function confirmPreview(threadId: string) {
  return apiRequest<ConfirmPlanResponse>(`/plans/preview/${threadId}/confirm`, { method: 'POST' });
}

export function listFeedback(planId: number) {
  return apiRequest<FeedbackRead[]>(`/plans/${planId}/feedback`);
}

export function patchTask(planId: number, taskId: number, body: TaskUpdateRequest) {
  return apiRequest<TaskRead>(`/plans/${planId}/tasks/${taskId}`, { method: 'PATCH', body });
}

export function submitFeedback(planId: number, body: FeedbackCreate) {
  return apiRequest<FeedbackSubmitResponse>(`/plans/${planId}/feedback`, {
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
  return apiRequest<ReplanResponse>(`/plans/${planId}/replan`, { method: 'POST', body });
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
const FALLBACK_CODES = new Set(['no_stream', 'network_error', 'stream_error']);

/**
 * Drive a job to completion: stream its SSE stages, then read the final status.
 * Falls back to polling when streaming is unavailable or the stream breaks.
 * Returns the finished `JobStatus` (its `result` holds the payload).
 */
export async function runJob(
  job: JobAccepted,
  onStage?: (stage: string, data: any) => void,
  signal?: AbortSignal,
): Promise<JobStatus> {
  const statusPath = `/plans/generation/${job.job_id}`;
  try {
    await apiStream(
      `/plans/generation/${job.job_id}/events`,
      { onStage: onStage ?? (() => undefined) },
      signal,
    );
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
