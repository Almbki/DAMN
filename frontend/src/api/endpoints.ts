import { apiRequest } from '@/api/client';
import type {
  FeedbackCreate,
  FeedbackSubmitResponse,
  InsightRead,
  PlanGenerateRequest,
  PlanGenerateResponse,
  PlanListItem,
  PlanRead,
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
