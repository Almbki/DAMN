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

/** Backend `TaskKind`: how a goal/task repeats over time. */
export type TaskKind = 'one_off' | 'long_term' | 'routine';

/** Backend feedback policy route. */
export type ReplanDecision = 'none' | 'micro_adjust' | 'full_replan';

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
  /** Truthful production provenance (null for legacy/mock-shaped rows). */
  prediction_source?: string | null;
  prediction_mode?: string | null;
  /** Active execution start (survives a refresh; read-only). */
  started_at?: string | null;
  is_flexible: boolean;
  task_kind?: TaskKind | null;
  series_id?: string | null;
  series_index?: number | null;
  occurrence_date?: string | null;
  target_amount?: number | null;
  target_unit?: string | null;
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
  start_date?: string | null;
  task_kind?: TaskKind | null;
  daily_target_minutes?: number | null;
  recurrence_weekdays?: number[] | null;
  target_amount?: number | null;
  target_unit?: string | null;
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
  /** Validated Level 1 trait profile (authoritative stable traits). */
  trait_profile?: Record<string, unknown> | null;
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
  /** Level 2 stress projection (0..1); compatibility/display only. */
  state_stress: number;
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
  // --- compatibility projections (do not use as the product state) ---
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
  state_stress: number;
  self_efficacy: number;
  update_count: number;
  degraded: boolean;
  // --- real three-layer model snapshots (authoritative) ---
  trait: TraitSnapshot | null;
  state: DynamicStateSnapshot | null;
  model_metadata: ModelMetadata[];
}

/** Level 1 / Level 2 / Level 3 metadata (artifact identity + status). */
export type ModelStatus = 'ok' | 'degraded' | 'unavailable' | 'not_fitted';

export interface ModelMetadata {
  level: 'level1' | 'level2' | 'level3';
  model_version: string;
  artifact_version: string;
  artifact_hash: string;
  feature_version: string;
  mode: string | null;
  status: ModelStatus;
  degraded_reason: string | null;
}

export interface TraitDomain {
  theta: number;
  se: number;
  ci95: [number, number] | null;
  items_answered: number;
}

export type TraitDomainKey = 'N' | 'E' | 'O' | 'A' | 'C';

export interface TraitSnapshot {
  model_version: string;
  schema_version: string;
  domains: Record<TraitDomainKey, TraitDomain>;
  calibration: Record<string, unknown>;
  metadata: ModelMetadata;
}

export interface StateEstimate {
  value: number;
  uncertainty: number;
  evidence_availability: string;
  evidence_count: number;
  conflict: boolean;
}

export interface DynamicStateSnapshot {
  date: string;
  fatigue: StateEstimate;
  stress: StateEstimate;
  self_efficacy: StateEstimate;
  next_day_prior: Record<string, number>;
  next_day_uncertainty: Record<string, number>;
  model_version: string;
  config_version: string;
  cold_start: boolean;
  gap_days: number;
  profile_json: Record<string, unknown>;
  metadata: ModelMetadata;
}

/** `GET /users/me/model-runtime` (developer/debug surface). */
export interface ModelRuntimeLayer {
  level: 'level1' | 'level2' | 'level3';
  model_version: string;
  artifact_version: string;
  artifact_hash: string;
  feature_version: string;
  status: ModelStatus;
  mode: string | null;
  degraded_reason: string | null;
}

export interface ShadowSummary {
  runs: number;
  success_rate: number | null;
  failures: number;
  mean_disagreement: number | null;
  status: 'ok' | 'no_runtime_data';
}

export interface ModelRuntimeRead {
  requested_mode: string;
  effective_mode: string;
  mode_reason: string | null;
  layers: ModelRuntimeLayer[];
  shadow_summary: ShadowSummary;
}

/** Level 1 CAT assessment wire contract. */
export interface TraitAssessmentItem {
  item_id: string;
  text: string;
  text_en: string;
  domain: TraitDomainKey;
  domain_name: string;
  facet: string;
  facet_name: string;
}

export interface TraitAssessmentDomainProgress {
  answered: number;
  stopped: boolean;
  domain_name: string;
}

export interface TraitAssessmentProgress {
  answered: number;
  remaining_min: number;
  remaining_max: number;
  completed_domains: number;
  total_domains: number;
  current_domain: TraitDomainKey | null;
  domains: Partial<Record<TraitDomainKey, TraitAssessmentDomainProgress>>;
}

export interface TraitAssessmentRead {
  assessment_id: string;
  status: 'in_progress' | 'completed' | 'abandoned';
  next_item: TraitAssessmentItem | null;
  progress: TraitAssessmentProgress;
  trait_profile: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface TraitAssessmentAnswerRequest {
  item_id: string;
  response: number;
}

export interface TraitReassessmentEligibilityRead {
  eligible: boolean;
  cooldown_days: number;
  last_completed_at: string | null;
  next_eligible_at: string | null;
}

export interface SyntheticScenarioInfo {
  name: string;
  description: string;
  scenario_version: string;
  days: number;
  tasks: number;
}

export interface SyntheticScenarioList {
  scenarios: SyntheticScenarioInfo[];
}

export interface SyntheticImportSummary {
  scenario: string;
  days_imported: number;
  tasks_imported: number;
  executions_imported: number;
  feedback_imported: number;
  level1_status: string;
  level2_status: string;
  level2_observed_on: string | null;
  shadow_runs_before: number;
  shadow_runs_after: number;
  warnings: string[];
}

export interface SyntheticResetSummary {
  deleted: Record<string, number>;
  level1_status: string;
  level2_status: string;
  warnings: string[];
}

export interface SyntheticStatus {
  enabled: boolean;
  synthetic_present: boolean;
  counts: Record<string, number>;
}

/** Body for `PATCH /users/me`; sending any field re-initialises the state. */
export interface ProfileUpdateRequest {
  mbti_type?: string | null;
  mbti_dims?: MbtiDims | null;
  identity?: string | null;
  trait_profile?: Record<string, unknown> | null;
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
  /** Partial completion (0..1); backend records a TaskExecution row. */
  completion_rate?: number | null;
  /** Optional observed interruptions; null/omitted = not observed. */
  interruption_count?: number | null;
  difficulty_feedback?: number;
  stress_before?: number;
  stress_after?: number;
  failure_reason?: string;
  started_at?: string;
  finished_at?: string;
  /** Explicit user overrides (editable in `PATCH /plans/{id}/tasks/{task_id}`). */
  title?: string;
  description?: string | null;
  estimated_duration?: number;
  priority?: number;
  cognitive_load?: CognitiveLoad;
  scheduled_date?: string | null;
  start_time?: string | null;
  end_time?: string | null;
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
  start_date?: string | null;
  task_kind?: TaskKind | null;
  daily_target_minutes?: number | null;
  recurrence_weekdays?: number[] | null;
  target_amount?: number | null;
  target_unit?: string | null;
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
  start_date?: string | null;
  task_kind?: TaskKind | null;
  daily_target_minutes?: number | null;
  recurrence_weekdays?: number[] | null;
  target_amount?: number | null;
  target_unit?: string | null;
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
  start_date?: string | null;
  task_kind?: TaskKind | null;
  daily_target_minutes?: number | null;
  recurrence_weekdays?: number[] | null;
  target_amount?: number | null;
  target_unit?: string | null;
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

/** Per-task reason attached to a daily feedback submission. */
export interface TaskReason {
  task_id: number;
  reason: string;
  note?: string | null;
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
  task_reasons?: TaskReason[];
}

export interface FeedbackRead extends FeedbackCreate {
  id: number;
  user_id: number;
  plan_id: number;
  completion_rate: number;
  task_reasons: TaskReason[];
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
  /** Set when `?stream_replan=true`; poll/stream this job for the replan result. */
  replan_job_id: string | null;
  replan_eligibility: ReplanEligibilityRead | null;
  /** Agent decision from the feedback loop (route / severity / reasons). */
  adjustment: FeedbackAdjustmentRead | null;
  /** Policy route chosen for this submission. */
  replan_decision: ReplanDecision;
  /** Why the policy chose that route (or the graph's reason when it ran). */
  replan_reason: string | null;
}

/**
 * Result payload of a `kind="feedback_replan"` streaming job (the value in
 * `JobStatus.result`). Mirrors the backend runner's dict.
 */
export interface FeedbackReplanJobResult {
  replan_triggered: boolean;
  replan_plan_id: number | null;
  replan_decision: ReplanDecision;
  replan_reason: string | null;
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
  start_date?: string | null;
  task_kind?: TaskKind | null;
  daily_target_minutes?: number | null;
  recurrence_weekdays?: number[] | null;
  target_amount?: number | null;
  target_unit?: string | null;
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
  /** Local `HH:MM` at which the daily feedback reminder fires. */
  feedback_time?: string | null;
  feedback_enabled?: boolean;
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
  task_kind?: TaskKind | null;
  series_id?: string | null;
  series_index?: number | null;
  occurrence_date?: string | null;
  target_amount?: number | null;
  target_unit?: string | null;
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

/**
 * `GET /schedules` — a fixed course / busy block.
 *
 * `weekdays` is `0..6` with **0 = Monday**. `null`/empty means the event is a
 * one-off on `start_date` (or on every day of `start_date..end_date`).
 * `start_time`/`end_time` come back as `HH:MM:SS`.
 */
export interface ScheduleEventRead {
  id: number;
  user_id: number;
  title: string;
  /** Teacher / lecturer; `null` when the timetable row did not carry one. */
  teacher: string | null;
  event_kind: string;
  start_date: string | null;
  end_date: string | null;
  start_time: string;
  end_time: string;
  weekdays: number[] | null;
  source: string;
  external_uid: string | null;
  location: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

/** `POST /schedules/import` — per-row outcomes; conflicts never block. */
export interface ScheduleImportResult {
  imported: number;
  updated: number;
  skipped: number;
  warnings: string[];
  conflicts: string[];
}
