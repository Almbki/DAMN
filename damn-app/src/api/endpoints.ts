/**
 * 接口清单 —— 每个函数对应 `docs/api.md` 里的一个端点。
 *
 * 页面**不要**直接调 `request()`，一律走这里：路径、方法、超时都只在这一个地方写，
 * 后端改了地址结构也只需改这里。
 *
 * 实测（`.shots/smoke-api.ps1`）确认过的行为：
 *  - `POST /plans/generate` 是**同步**的，约 1.5 s 返回，`status === "completed"`
 *    且 `plan` 已经内联 —— 所以 MVP **不需要 SSE** 拉进度；
 *  - `PATCH .../tasks/{id}` 传 `completed: true` 后 `status` 变成 `completed`；
 *  - `/health` 在**根路径**，其余都在 `/api/v1` 下。
 */

import { GENERATE_TIMEOUT_MS } from './config';
import { request } from './client';
import type {
  FeedbackCreate,
  FeedbackRead,
  FeedbackSubmitResponse,
  GoalRead,
  HealthResponse,
  InsightRead,
  LoginRequest,
  PlanGenerateRequest,
  PlanGenerateResponse,
  PlanListItem,
  PlanRead,
  RegisterRequest,
  ReplanEligibilityRead,
  ReplanRequest,
  ReplanResponse,
  TaskRead,
  TaskUpdateRequest,
  TokenResponse,
  UserRead,
  UserUpdate,
} from './types';

/* ----------------------------------------------------------------- system */

export function health(): Promise<HealthResponse> {
  return request<HealthResponse>('/health', { root: true });
}

/* ------------------------------------------------------------------- auth */

export function register(body: RegisterRequest): Promise<UserRead> {
  return request<UserRead>('/auth/register', { method: 'POST', body });
}

export function login(body: LoginRequest): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/login', { method: 'POST', body });
}

/* ------------------------------------------------------------------ users */

export function getMe(token: string): Promise<UserRead> {
  return request<UserRead>('/users/me', { token });
}

export function updateMe(token: string, body: UserUpdate): Promise<UserRead> {
  return request<UserRead>('/users/me', { method: 'PATCH', token, body });
}

/* ------------------------------------------------------------------ plans */

export function generatePlan(
  token: string,
  body: PlanGenerateRequest,
): Promise<PlanGenerateResponse> {
  return request<PlanGenerateResponse>('/plans/generate', {
    method: 'POST',
    token,
    body,
    // 后端要跑完 LangGraph 才返回，给足超时
    timeoutMs: GENERATE_TIMEOUT_MS,
  });
}

/** 只返回列表项，没有 tasks —— 要任务明细得再调 `getPlan`。 */
export function listPlans(token: string): Promise<PlanListItem[]> {
  return request<PlanListItem[]>('/plans', { token });
}

export function getPlan(token: string, planId: number): Promise<PlanRead> {
  return request<PlanRead>(`/plans/${planId}`, { token });
}

export function updateTask(
  token: string,
  planId: number,
  taskId: number,
  body: TaskUpdateRequest,
): Promise<TaskRead> {
  return request<TaskRead>(`/plans/${planId}/tasks/${taskId}`, {
    method: 'PATCH',
    token,
    body,
  });
}

/* --------------------------------------------------------------- feedback */

export function submitFeedback(
  token: string,
  planId: number,
  body: FeedbackCreate,
): Promise<FeedbackSubmitResponse> {
  return request<FeedbackSubmitResponse>(`/plans/${planId}/feedback`, {
    method: 'POST',
    token,
    body,
  });
}

export function listFeedback(token: string, planId: number): Promise<FeedbackRead[]> {
  return request<FeedbackRead[]>(`/plans/${planId}/feedback`, { token });
}

/* ----------------------------------------------------------------- replan */

export function getReplanEligibility(
  token: string,
  planId: number,
): Promise<ReplanEligibilityRead> {
  return request<ReplanEligibilityRead>(`/plans/${planId}/replan/eligibility`, { token });
}

/** 冷却期内会抛 `ApiError`，`code === 'replan_not_eligible'`（HTTP 409）。 */
export function replan(
  token: string,
  planId: number,
  body: ReplanRequest,
): Promise<ReplanResponse> {
  return request<ReplanResponse>(`/plans/${planId}/replan`, {
    method: 'POST',
    token,
    body,
    timeoutMs: GENERATE_TIMEOUT_MS,
  });
}

/* --------------------------------------------------------------- insights */

export function getInsights(token: string, planId: number): Promise<InsightRead> {
  return request<InsightRead>(`/plans/${planId}/insights`, { token });
}

/* ---------------------------------------------------------------- helpers */

/** 补齐了 `tasks` / `goals` 的计划 —— 页面里可以放心直接 `.map`。 */
export type FullPlan = PlanRead & { tasks: TaskRead[]; goals: GoalRead[] };

/**
 * schema 里 `PlanRead.tasks` / `.goals` 是**可选**的（没有任务时后端可能不返回这两个键）。
 * 页面里到处写 `?? []` 不如在入口处统一成数组。
 */
export function normalizePlan(plan: PlanRead): FullPlan {
  return { ...plan, tasks: plan.tasks ?? [], goals: plan.goals ?? [] };
}
