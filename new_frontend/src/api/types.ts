/**
 * Shapes mirror the FastAPI schemas in `docs/api.md` / `/openapi.json`.
 * These are the contract the mock adapter and the HTTP adapter both satisfy.
 */

export type TaskStatus =
  | 'pending'
  | 'scheduled'
  | 'in_progress'
  | 'completed'
  | 'skipped'
  | 'failed';

/** Backend `CognitiveLoad` also includes `restorative`. */
export type CognitiveLoad = 'low' | 'medium' | 'high' | 'restorative';

/** Backend `GoalStatus`; `draft` marks a not-yet-decomposed item (待拆解). */
export type GoalStatus = 'draft' | 'active' | 'completed' | 'archived' | 'cancelled';

export interface StandardRead {
  id: number;
  description: string;
  estimated_duration: number | null;
  completed: boolean;
  order_index: number;
}

export interface TaskRead {
  id: number;
  plan_id: number;
  goal_id: number | null;
  parent_task_id: number | null;
  title: string;
  description: string | null;
  estimated_duration: number;
  predicted_duration: number | null;
  cognitive_load: CognitiveLoad;
  priority: number;
  scheduled_date: string | null;
  start_time: string | null;
  end_time: string | null;
  status: TaskStatus;
  completion_probability: number | null;
  is_flexible: boolean;
  order_index: number;
  standards: StandardRead[];
}

export interface GoalRead {
  id: number;
  title: string;
  description: string | null;
  goal_type: string;
  priority: number;
  status: string;
  deadline: string | null;
  estimated_minutes: number | null;
}

export interface PlanRead {
  id: number;
  user_id: number;
  version: number;
  status: string;
  title: string | null;
  start_date: string;
  end_date: string;
  parent_plan_id: number | null;
  confidence: number | null;
  created_at: string;
  tasks: TaskRead[];
  goals: GoalRead[];
}

export interface UserRead {
  id: number;
  email: string;
  display_name: string | null;
  execution_weight: number;
  profile: Record<string, unknown>;
  /** Portrait fields (see `ProfileRead`); absent/`null` when unset. */
  mbti_type?: string | null;
  mbti_dims?: MbtiDims | null;
  identity?: string | null;
  created_at: string;
}

/**
 * MBTI dimension weights. Each is `0..1`, weighted toward the FIRST letter of
 * its pair (I / S / T / J): `ie: 0.65` means 65% I, 35% E. Omitted keys mean the
 * backend keeps its default for that axis.
 */
export interface MbtiDims {
  ie?: number;
  sn?: number;
  tf?: number;
  jp?: number;
}

/** Static 基础画像 fields (`GET /users/me/profile`). */
export interface UserProfileRead {
  mbti_type: string | null;
  mbti_dims: MbtiDims | null;
  identity: string | null;
}

/**
 * Feedback-updated adaptive user state, returned alongside the profile.
 * Every metric is `0..1` except `duration_factor` (unitless multiplier) and
 * `update_count`.
 */
export interface UserStateRead {
  duration_factor: number;
  completion_prob: number;
  stress_baseline: number;
  energy_drain_rate: number;
  proactive_score: number;
  procrastination_tendency: number;
  preferred_time_slots: Record<string, string>;
  stress_response: number;
  state_energy: number;
  state_fatigue: number;
  self_efficacy: number;
  update_count: number;
  /** True while `update_count < 3` (冷启动校准中). */
  degraded: boolean;
}

/**
 * `GET /users/me/profile` response (backend `ProfileRead`); 404 when the user has
 * no profile yet. This is a **flat** object: the static portrait fields are
 * merged with the adaptive state, the backend does NOT nest `{ profile, state }`.
 */
export interface ProfileRead {
  mbti_type: string | null;
  mbti_dims: MbtiDims | null;
  identity: string | null;
  // --- adaptive state (EWMA-updated by feedback) ---
  duration_factor: number;
  completion_prob: number;
  stress_baseline: number;
  energy_drain_rate: number;
  proactive_score: number;
  procrastination_tendency: number;
  preferred_time_slots: Record<string, string>;
  stress_response: number;
  state_energy: number;
  state_fatigue: number;
  self_efficacy: number;
  update_count: number;
  /** True while `update_count < 3` (冷启动校准中). */
  degraded: boolean;
}

/** Body for `PATCH /users/me`; sending any field re-initialises the state. */
export interface ProfileUpdateRequest {
  mbti_type?: string | null;
  mbti_dims?: MbtiDims | null;
  identity?: string | null;
}

export interface DailyCompletionRead {
  date: string;
  total_tasks: number;
  completed_tasks: number;
  completion_rate: number;
  planned_minutes: number;
}

/** Backend `DataSufficiency` - is there enough history to trust a signal. */
export interface DataSufficiency {
  samples: number;
  min_samples: number;
  sufficient: boolean;
}

/** Mirrors `InsightRead` from the backend (`GET /plans/{plan_id}/insights`). */
export interface InsightRead {
  plan_id: number;
  total_tasks: number;
  completed_tasks: number;
  completion_rate: number;
  total_planned_minutes: number;
  total_actual_minutes: number;
  avg_stress: number | null;
  avg_energy: number | null;
  high_cognitive_minutes: number;
  predicted_vs_actual_ratio: number | null;
  cognitive_load_breakdown: Record<string, number>;
  daily: DailyCompletionRead[];
  recommendations: string[];
  /** Whether there is enough recorded history to trust the numbers above. */
  data_sufficiency?: DataSufficiency | null;
  /** Human-readable reasons behind the summary (Chinese UI copy). */
  drivers?: string[] | null;
}

export interface TaskUpdateRequest {
  status?: TaskStatus;
  completed?: boolean;
  actual_duration?: number;
  difficulty_feedback?: number;
  stress_before?: number;
  stress_after?: number;
  failure_reason?: string;
  started_at?: string;
  finished_at?: string;
  standard_updates?: { id: number; completed: boolean }[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name?: string | null;
  execution_weight?: number;
  profile?: Record<string, unknown>;
  /** Optional 基础画像 fields accepted at registration. */
  mbti_type?: string | null;
  mbti_dims?: MbtiDims | null;
  identity?: string | null;
}

export interface PlanListItem {
  id: number;
  version: number;
  status: string;
  title: string | null;
  start_date: string;
  end_date: string;
  confidence: number;
  created_at: string;
  task_count: number;
  completed_count: number;
}

export interface GoalCreate {
  title: string;
  description?: string | null;
  goal_type?: string;
  deadline?: string | null;
  priority?: number;
  estimated_minutes?: number | null;
  subject?: string | null;
  task_type?: string | null;
}

/** Body for `POST /goals` (backend `GoalCreate`). */
export interface GoalCreateRequest {
  title: string;
  description?: string | null;
  goal_type?: string;
  deadline?: string | null;
  priority?: number;
  estimated_minutes?: number | null;
  subject?: string | null;
  task_type?: string | null;
  /** `draft` creates a 待拆解 item; `active` a real goal. */
  status?: GoalStatus;
}

/** Body for `PATCH /goals/{goalId}` (backend `GoalUpdate`; all optional). */
export interface UpdateGoalRequest {
  title?: string | null;
  description?: string | null;
  status?: GoalStatus | null;
  deadline?: string | null;
  priority?: number | null;
  estimated_minutes?: number | null;
  subject?: string | null;
  task_type?: string | null;
}

export interface PlanGenerateRequest {
  goals: GoalCreate[];
  start_date?: string | null;
  end_date?: string | null;
  plan_title?: string | null;
  available_minutes_per_day?: number;
  daily_limit_minutes?: number;
  buffer_minutes?: number;
  high_cognitive_max_per_day?: number;
  user_profile?: Record<string, unknown>;
  execution_weight?: number | null;
}

export interface PlanGenerateResponse {
  job_id: string;
  status: string;
  plan_id: number | null;
  events_url: string;
  plan: PlanRead | null;
}

export interface FeedbackCreate {
  date: string;
  completion_rate?: number;
  stress_level?: number | null;
  energy_level?: number | null;
  delay_reason?: string | null;
  free_text?: string | null;
  sleep_hours?: number | null;
  dominant_time_of_day?: string | null;
}

export interface FeedbackRead extends FeedbackCreate {
  id: number;
  user_id: number;
  plan_id: number;
  completion_rate: number;
  created_at: string;
}

export interface ReplanEligibilityRead {
  eligible: boolean;
  reason: string;
  next_eligible_at: string | null;
  last_replan_at: string | null;
  cooldown_hours: number;
}

/** Backend `FeedbackAdjustmentRead` - the agent's decision on a submission. */
export interface FeedbackAdjustmentRead {
  route: string;
  severity: string;
  reasons: string[];
  source: string;
  new_plan_id: number | null;
  degraded: boolean;
}

export interface FeedbackSubmitResponse {
  feedback: FeedbackRead;
  replan_triggered: boolean;
  replan_plan_id: number | null;
  replan_eligibility: ReplanEligibilityRead | null;
  /** Agent decision from the feedback loop (route / severity / reasons). */
  adjustment: FeedbackAdjustmentRead | null;
}

export type ReplanTriggerType = 'manual' | 'feedback_triggered' | 'scheduled' | 'system';

export interface ReplanRequest {
  trigger_type?: ReplanTriggerType;
  reason?: string | null;
  from_date?: string | null;
}

export interface ReplanResponse {
  plan_id: number;
  old_version: number;
  new_version: number;
  changed_task_ids: number[];
  reason: string;
  trigger_type: ReplanTriggerType;
}

/**
 * Contract for endpoints the frontend currently mocks. See
 * docs/design/backend-api-gaps.md for the exact shapes to implement.
 */

export interface GoalDetailRead {
  id: number;
  title: string;
  description: string | null;
  goal_type: string;
  status: GoalStatus;
  deadline: string | null;
  priority: number;
  estimated_minutes: number | null;
  created_at: string;
}

export interface SituationTrendPoint {
  date: string;
  energy: number | null;
  stress: number | null;
  efficacy: number | null;
}

export interface SituationTrendRead {
  points: SituationTrendPoint[];
  samples: number;
  min_samples: number;
  sufficient: boolean;
  drivers: string[];
}

export interface PlanChangeDayRead {
  date: string;
  added: number;
  moved: number;
  removed: number;
  summary: string;
  task_ids: number[];
}

export interface PlanChangeRead {
  id: number;
  trigger_type: ReplanTriggerType;
  reason: string;
  old_version: number;
  new_version: number;
  created_at: string;
  days: PlanChangeDayRead[];
}

/** `GET`/`PUT /users/me/preferences` (backend `SchedulingPreferences`). */
export interface SchedulingPreferences {
  available_minutes_per_day: number;
  daily_limit_minutes: number;
  buffer_minutes: number;
  high_cognitive_max_per_day: number;
  sleep_start?: string | null;
  sleep_end?: string | null;
}

/** `POST /plans/preview` — a not-yet-persisted plan the user can adjust. */
export interface PreviewTaskRead {
  order_index: number;
  title: string;
  description: string | null;
  goal_id: number | null;
  subject: string | null;
  cognitive_load: CognitiveLoad;
  priority: number;
  estimated_duration: number;
  predicted_duration: number | null;
  completion_probability: number | null;
  recommended_time_slot: string | null;
  standards: string[];
  scheduled_date: string | null;
  start_time: string | null;
  end_time: string | null;
}

export interface PreviewViolationRead {
  rule?: string;
  code?: string;
  message?: string;
  severity?: string;
}

export interface PreviewRead {
  thread_id: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  tasks: PreviewTaskRead[];
  confidence: number;
  adjustment_count: number;
  max_adjustments: number;
  can_adjust: boolean;
  violations: PreviewViolationRead[];
}

export interface PreviewResponse {
  thread_id: string;
  preview: PreviewRead;
  plan_id: number | null;
  goals_persisted: number;
  degraded: boolean;
  warnings: string[];
}

export interface AdjustResponse {
  thread_id: string;
  preview: PreviewRead | null;
  budget_exhausted: boolean;
  final_plan: PlanRead | null;
  degraded: boolean;
  warnings: string[];
}

export interface ConfirmPlanResponse {
  plan: PlanRead;
  adjustment_count: number;
  degraded: boolean;
  warnings: string[];
}

/**
 * `POST /plans/preview` (and `/adjust`) now enqueue an async job instead of
 * blocking until the draft is ready. `status_url` is the polling fallback for
 * platforms where streaming is unavailable.
 */
export type JobAccepted = {
  job_id: string;
  status: string;
  events_url: string;
  status_url: string;
};

/** `GET /plans/generation/{job_id}` — one generation job's current state. */
export type JobStatus = {
  job_id: string;
  kind: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result: Record<string, unknown> | null;
  error: string | null;
  events: Record<string, unknown>[];
};

/** SSE stage name; e.g. `goal_analysis` ... `rule_validation`, `completed`. */
export type PlanStage = string;
