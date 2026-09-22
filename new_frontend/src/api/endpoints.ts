import { apiPollJob, apiRequest, apiStream, isApiError } from '@/api/client';
import type {
  AdjustResponse,
  ConfirmPlanResponse,
  FeedbackCreate,
  FeedbackRead,
  FeedbackSubmitResponse,
  InsightRead,
  JobAccepted,
  JobStatus,
  PlanGenerateRequest,
  PlanGenerateResponse,
  PlanListItem,
  PlanRead,
  PreviewResponse,
  ProfileUpdateRequest,
  RegisterRequest,
  ReplanEligibilityRead,
  ReplanRequest,
  ReplanResponse,
  TaskRead,
  TaskUpdateRequest,
  TokenResponse,
  UserProfileResponse,
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

/** 基础画像 + adaptive state; the caller treats a 404 as "no profile yet". */
export function getMyProfile() {
  return apiRequest<UserProfileResponse>('/users/me/profile');
}

/** Sending any field re-initialises the backend state from the new profile. */
export function updateMyProfile(body: ProfileUpdateRequest) {
  return apiRequest<UserRead>('/users/me', { method: 'PATCH', body });
}

export function listPlans() {
  return apiRequest<PlanListItem[]>('/plans');
}

export function getPlan(planId: number) {
  return apiRequest<PlanRead>(`/plans/${planId}`);
}

export function generatePlan(body: PlanGenerateRequest) {
  return apiRequest<PlanGenerateResponse>('/plans/generate', { method: 'POST', body });
}

/** 拆解：先出一版**不落库**的草稿（`POST /plans/preview`）。 */
export function previewPlan(body: PlanGenerateRequest) {
  return apiRequest<PreviewResponse>('/plans/preview', { method: 'POST', body });
}

/** 对同一 `thread_id` 带反馈再拆一版；预算耗尽时会直接返回 `final_plan`。 */
export function adjustPreview(threadId: string, feedback: string) {
  return apiRequest<AdjustResponse>(`/plans/preview/${threadId}/adjust`, {
    method: 'POST',
    body: { thread_id: threadId, feedback },
  });
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

/** One-shot status fetch for a generation job. */
export function fetchJobStatus(jobId: string) {
  return apiRequest<JobStatus>(`/plans/generation/${jobId}`);
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
    return apiPollJob(statusPath, { signal });
  }
  return fetchJobStatus(job.job_id);
}
