/**
 * 后端 wire 类型。
 *
 * ## 这里的每个字段都抄自真实 schema，不要凭 `docs/api.md` 手写
 *
 * 权威来源是运行中的服务：`http://192.168.9.67:8000/openapi.json`
 * （工程根留了一份快照 `damn-app/.openapi.json`）。跑
 * `.shots/smoke-api.ps1` 可以顺带校对真实响应。
 *
 * `docs/api.md` 与 schema 已经对不上几处，实测为准：
 *  - 健康检查在**根路径** `/health`，不在 `/api/v1` 下；
 *  - `TaskRead` 有 `description` / `parent_task_id` / `is_flexible`，文档没写；
 *  - `GET /plans/{id}` 的 `tasks` / `goals` 在 schema 里**可选**（无任务时可能缺省）。
 */

/** `GET /health` */
export type HealthResponse = {
  status: string;
  app: string;
  version: string;
  environment: string;
};

/** 后端每个非 2xx 响应统一用这个信封（Pydantic 422 除外，见 `client.ts`）。 */
export type ErrorResponse = {
  code: string;
  message: string;
  detail?: unknown;
};

/* ------------------------------------------------------------------ 枚举 */

export type GoalType = 'long_term' | 'short_term' | 'project' | 'habit' | 'other';
export type GoalStatus = 'active' | 'completed' | 'archived' | 'cancelled';
export type PlanStatus = 'draft' | 'active' | 'superseded' | 'completed' | 'archived';
export type TaskStatus = 'pending' | 'scheduled' | 'in_progress' | 'completed' | 'skipped' | 'failed';
/** `restorative` = 当作认知休息的活动（运动、听音乐）。 */
export type CognitiveLoad = 'high' | 'medium' | 'low' | 'restorative';
export type Priority = 1 | 2 | 3 | 4;
export type TimeOfDay = 'morning' | 'afternoon' | 'evening' | 'night';
export type ReplanTriggerType = 'manual' | 'feedback_triggered' | 'scheduled' | 'system';

/* -------------------------------------------------------------------- auth */

export type RegisterRequest = {
  email: string;
  /** 8–128 字符 */
  password: string;
  display_name?: string | null;
  /** 0..1，默认 0.5 */
  execution_weight?: number;
  profile?: Record<string, unknown>;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  /** 秒。默认 604800（7 天），**没有 refresh 接口** —— 过期就重新登录。 */
  expires_in: number;
};

/* ------------------------------------------------------------------- users */

export type UserRead = {
  id: number;
  email: string;
  display_name?: string | null;
  execution_weight: number;
  profile: Record<string, unknown>;
  created_at: string;
};

export type UserUpdate = {
  display_name?: string | null;
  execution_weight?: number | null;
  profile?: Record<string, unknown> | null;
};

/* ------------------------------------------------------------------- plans */

export type GoalCreate = {
  title: string;
  /** 用 `\n` 分段 —— 后端会把每一行拆成一条 task standard（实测）。 */
  description?: string | null;
  goal_type?: GoalType;
  deadline?: string | null;
  priority?: Priority;
  estimated_minutes?: number | null;
  subject?: string | null;
  task_type?: string | null;
};

export type GoalRead = {
  id: number;
  title: string;
  description?: string | null;
  goal_type: GoalType;
  deadline?: string | null;
  priority: Priority;
  status: GoalStatus;
  estimated_minutes?: number | null;
};

export type TaskStandardRead = {
  id: number;
  description: string;
  estimated_duration: number;
  completed: boolean;
  order_index: number;
};

export type TaskRead = {
  id: number;
  plan_id: number;
  goal_id?: number | null;
  parent_task_id?: number | null;
  title: string;
  description?: string | null;
  /** 用户/目标给出的估时 */
  estimated_duration: number;
  /** 模型修正后的预测时长。**界面展示用这个**，没有时才回落到 estimated。 */
  predicted_duration?: number | null;
  cognitive_load: CognitiveLoad;
  priority: Priority;
  scheduled_date?: string | null;
  /** `"08:00:00"` —— `new Date()` 解析不了，见 `format.ts` */
  start_time?: string | null;
  end_time?: string | null;
  status: TaskStatus;
  completion_probability?: number | null;
  is_flexible: boolean;
  order_index: number;
  standards?: TaskStandardRead[];
};

export type PlanRead = {
  id: number;
  user_id: number;
  version: number;
  status: PlanStatus;
  title?: string | null;
  /** `"2026-09-19"` */
  start_date: string;
  end_date: string;
  parent_plan_id?: number | null;
  confidence: number;
  created_at: string;
  tasks?: TaskRead[];
  goals?: GoalRead[];
};

export type PlanListItem = {
  id: number;
  version: number;
  status: PlanStatus;
  title?: string | null;
  start_date: string;
  end_date: string;
  confidence: number;
  created_at: string;
  task_count: number;
  completed_count: number;
};

export type PlanGenerateRequest = {
  goals: GoalCreate[];
  /** 默认今天 */
  start_date?: string | null;
  /** 默认 start_date + 13 天 */
  end_date?: string | null;
  plan_title?: string | null;
  available_minutes_per_day?: number;
  daily_limit_minutes?: number;
  buffer_minutes?: number;
  high_cognitive_max_per_day?: number;
  user_profile?: Record<string, unknown>;
  execution_weight?: number | null;
};

export type PlanGenerateResponse = {
  job_id: string;
  /** 实测同步跑完即为 `"completed"`，此时 `plan` 已经内联返回。 */
  status: string;
  plan_id?: number | null;
  /** 例：`/api/v1/plans/generation/<job_id>/events` */
  events_url: string;
  plan?: PlanRead | null;
};

export type TaskStandardUpdate = {
  id: number;
  completed: boolean;
};

export type TaskUpdateRequest = {
  status?: TaskStatus | null;
  /** 写 `true` 时后端会**同时写一条 TaskExecution**（ML 数据资产）。 */
  completed?: boolean | null;
  actual_duration?: number | null;
  difficulty_feedback?: number | null;
  stress_before?: number | null;
  stress_after?: number | null;
  failure_reason?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  standard_updates?: TaskStandardUpdate[] | null;
};

/* ---------------------------------------------------------------- feedback */

export type FeedbackCreate = {
  /** `"YYYY-MM-DD"` */
  date: string;
  completion_rate?: number;
  stress_level?: number | null;
  energy_level?: number | null;
  delay_reason?: string | null;
  free_text?: string | null;
  sleep_hours?: number | null;
  dominant_time_of_day?: TimeOfDay | null;
};

export type FeedbackRead = {
  id: number;
  user_id: number;
  plan_id: number;
  date: string;
  completion_rate: number;
  stress_level?: number | null;
  energy_level?: number | null;
  delay_reason?: string | null;
  free_text?: string | null;
  sleep_hours?: number | null;
  dominant_time_of_day?: TimeOfDay | null;
  created_at: string;
};

export type ReplanEligibilityRead = {
  eligible: boolean;
  reason: string;
  next_eligible_at?: string | null;
  last_replan_at?: string | null;
  /** 冷却时长，**按用户**计（不是按计划）。默认 24。 */
  cooldown_hours: number;
};

export type FeedbackSubmitResponse = {
  feedback: FeedbackRead;
  replan_triggered: boolean;
  replan_plan_id?: number | null;
  replan_eligibility?: ReplanEligibilityRead | null;
};

/* ------------------------------------------------------------------ replan */

export type ReplanRequest = {
  trigger_type?: ReplanTriggerType;
  reason?: string | null;
  from_date?: string | null;
};

export type ReplanResponse = {
  plan_id: number;
  old_version: number;
  new_version: number;
  changed_task_ids: number[];
  reason: string;
  trigger_type: ReplanTriggerType;
};

/* ---------------------------------------------------------------- insights */

export type DailyCompletionRead = {
  date: string;
  total_tasks: number;
  completed_tasks: number;
  completion_rate: number;
  planned_minutes: number;
};

export type InsightRead = {
  plan_id: number;
  total_tasks: number;
  completed_tasks: number;
  completion_rate: number;
  total_planned_minutes: number;
  total_actual_minutes: number;
  avg_stress?: number | null;
  avg_energy?: number | null;
  high_cognitive_minutes: number;
  /** Σ 实际 ÷ Σ 计划；> 1.3 说明时长系数偏低，< 0.7 偏高。 */
  predicted_vs_actual_ratio?: number | null;
  cognitive_load_breakdown: Record<string, number>;
  daily: DailyCompletionRead[];
  recommendations: string[];
};
