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

export type CognitiveLoad = 'low' | 'medium' | 'high';

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
  title: string;
  estimated_duration: number | null;
  predicted_duration: number | null;
  cognitive_load: CognitiveLoad | null;
  priority: number;
  scheduled_date: string | null;
  start_time: string | null;
  end_time: string | null;
  status: TaskStatus;
  completion_probability: number | null;
  standards: StandardRead[];
}

export interface GoalRead {
  id: number;
  title: string;
  goal_type: string;
  priority: number;
  status: string;
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
  created_at: string;
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
