import type { PlanRead, TaskRead, UserRead } from '@/api/types';

/**
 * Mock fixtures. Shapes match the FastAPI contract so swapping the mock adapter
 * for the HTTP adapter later is a provider change, not a page change.
 */

export const mockUser: UserRead = {
  id: 1,
  email: 'demo@damn.app',
  display_name: '演示用户',
  execution_weight: 0.5,
  profile: { available_minutes_per_day: 480, sleep_schedule: '23:30-07:30' },
  created_at: '2026-09-01T08:00:00Z',
};

/** A coarse self-assessment. Drives the wording of "why this, now". */
export type EnergyLevel = 'low' | 'medium' | 'high';
export type StressLevel = 'low' | 'medium' | 'high';

export const energyLabel: Record<EnergyLevel, string> = {
  low: '精力偏低',
  medium: '精力中等',
  high: '精力不错',
};

function standard(id: number, description: string, estimated: number, completed = false) {
  return { id, description, estimated_duration: estimated, completed, order_index: id };
}

export const mockTasks: TaskRead[] = [
  {
    id: 1,
    plan_id: 1,
    goal_id: 1,
    title: '慢跑 4 公里',
    estimated_duration: 30,
    predicted_duration: 33,
    cognitive_load: 'medium',
    priority: 3,
    scheduled_date: '2026-09-20',
    start_time: '07:30:00',
    end_time: '08:03:00',
    status: 'completed',
    completion_probability: 0.82,
    standards: [standard(1, '热身', 5, true), standard(2, '跑 4 公里', 25, true)],
  },
  {
    id: 2,
    plan_id: 1,
    goal_id: 1,
    title: '核心力量训练',
    estimated_duration: 25,
    predicted_duration: 28,
    cognitive_load: 'high',
    priority: 2,
    scheduled_date: '2026-09-20',
    start_time: '14:35:00',
    end_time: '15:03:00',
    status: 'scheduled',
    completion_probability: 0.71,
    standards: [
      standard(1, '动态热身', 5, true),
      standard(2, '平板支撑 3 组', 8),
      standard(3, '臀桥 3 组', 7),
      standard(4, '放松拉伸', 5),
    ],
  },
  {
    id: 3,
    plan_id: 1,
    goal_id: 1,
    title: '拉伸与放松',
    estimated_duration: 15,
    predicted_duration: 15,
    cognitive_load: 'low',
    priority: 3,
    scheduled_date: '2026-09-20',
    start_time: '15:10:00',
    end_time: '15:25:00',
    status: 'scheduled',
    completion_probability: 0.88,
    standards: [standard(1, '全身拉伸', 15)],
  },
  {
    id: 4,
    plan_id: 1,
    goal_id: 2,
    title: '阅读跑步姿势笔记',
    estimated_duration: 20,
    predicted_duration: 22,
    cognitive_load: 'low',
    priority: 4,
    scheduled_date: '2026-09-20',
    start_time: '20:00:00',
    end_time: '20:22:00',
    status: 'scheduled',
    completion_probability: 0.64,
    standards: [standard(1, '读第 3 章', 20)],
  },
  {
    id: 5,
    plan_id: 1,
    goal_id: 2,
    title: '记录今天的状态',
    estimated_duration: 5,
    predicted_duration: 5,
    cognitive_load: 'low',
    priority: 4,
    scheduled_date: '2026-09-20',
    start_time: '21:30:00',
    end_time: '21:35:00',
    status: 'scheduled',
    completion_probability: 0.9,
    standards: [standard(1, '填写精力与压力', 5)],
  },
];

export const mockPlan: PlanRead = {
  id: 1,
  user_id: 1,
  version: 3,
  status: 'active',
  title: '半马备赛 · 第 3 周',
  start_date: '2026-09-14',
  end_date: '2026-09-27',
  parent_plan_id: 2,
  confidence: 0.62,
  created_at: '2026-09-20T06:00:00Z',
  tasks: mockTasks,
  // NOTE: the backend mis-maps PlanRead.goals (titles come from the account's
  // oldest N goals). No page renders this field until that join is fixed.
  goals: [
    { id: 1, title: '半马备赛', goal_type: 'long_term', priority: 2, status: 'active' },
    { id: 2, title: '改善跑步姿势', goal_type: 'short_term', priority: 3, status: 'active' },
  ],
};

export const mockWhyNow = '昨天你只完成了 3/5，所以今天先排轻一点。这件事在 15:00 前做完就好。';
