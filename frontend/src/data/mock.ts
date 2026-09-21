import type { UserRead } from '@/api/types';
import { addDays, daysAgoISO, todayISO } from '@/domain/date';
import type { FeedbackSample } from '@/domain/insight';
import type { Completion } from '@/domain/stats';
import { NO_REPEAT, type Task } from '@/domain/task';

/**
 * Mock fixtures for the local task store. Shapes follow `domain/task.ts`; the
 * backend contract lives separately in `api/types.ts`.
 */

export const mockUser: UserRead = {
  id: 1,
  email: 'demo@damn.app',
  display_name: '演示用户',
  execution_weight: 0.5,
  profile: { available_minutes_per_day: 480, sleep_schedule: '23:30-07:30' },
  created_at: '2026-09-01T08:00:00Z',
};

export type EnergyLevel = 'low' | 'medium' | 'high';

export const mockPlanId = 1;

export const energyLabel: Record<EnergyLevel, string> = {
  low: '精力偏低',
  medium: '精力中等',
  high: '精力不错',
};

const today = todayISO();

export const mockTasks: Task[] = [
  {
    id: 1,
    title: '慢跑 4 公里',
    description: '轻松跑，保持能说话的配速。',
    notes: '',
    done: true,
    skipped: false,
    startDate: null,
    startTime: '07:30',
    dueDate: today,
    dueTime: '08:00',
    estimatedMinutes: 30,
    actualMinutes: 33,
    cognitiveLoad: 'medium',
    repeat: { ...NO_REPEAT, freq: 'daily', interval: 1 },
    tags: ['跑步'],
    order: 0,
    completedAt: today,
  },
  {
    id: 2,
    title: '核心力量训练',
    description: '平板支撑、臀桥、死虫式各三组。',
    notes: '如果腰不舒服就跳过臀桥。',
    done: false,
    skipped: false,
    startDate: null,
    startTime: null,
    dueDate: today,
    dueTime: '15:00',
    estimatedMinutes: 25,
    actualMinutes: null,
    cognitiveLoad: 'high',
    repeat: NO_REPEAT,
    tags: ['跑步', '力量'],
    order: 1,
    completedAt: null,
  },
  {
    id: 3,
    title: '拉伸与放松',
    description: '',
    notes: '',
    done: true,
    skipped: false,
    startDate: null,
    startTime: null,
    dueDate: today,
    dueTime: '15:10',
    estimatedMinutes: 15,
    actualMinutes: 14,
    cognitiveLoad: 'low',
    repeat: NO_REPEAT,
    tags: [],
    order: 2,
    completedAt: today,
  },
  {
    id: 4,
    title: '阅读跑步姿势笔记',
    description: '重点看第 3 章的落地方式。',
    notes: '',
    done: false,
    skipped: false,
    startDate: null,
    startTime: null,
    dueDate: addDays(today, 1),
    dueTime: null,
    estimatedMinutes: 20,
    actualMinutes: null,
    cognitiveLoad: 'low',
    repeat: NO_REPEAT,
    tags: ['阅读'],
    order: 3,
    completedAt: null,
  },
  {
    id: 5,
    title: '记录今天的状态',
    description: '',
    notes: '',
    done: false,
    skipped: false,
    startDate: null,
    startTime: null,
    dueDate: null,
    dueTime: null,
    estimatedMinutes: 5,
    actualMinutes: null,
    cognitiveLoad: 'low',
    repeat: { ...NO_REPEAT, freq: 'daily', interval: 1 },
    tags: [],
    order: 4,
    completedAt: null,
  },
  {
    id: 6,
    title: '提交项目汇报材料',
    description: '整理本周进展与下周计划。',
    notes: '需要先拿到设计稿。',
    done: false,
    skipped: false,
    startDate: daysAgoISO(2),
    startTime: null,
    dueDate: daysAgoISO(2),
    dueTime: '18:00',
    estimatedMinutes: 45,
    actualMinutes: null,
    cognitiveLoad: 'high',
    repeat: NO_REPEAT,
    tags: ['工作'],
    order: 5,
    completedAt: null,
  },
  {
    id: 7,
    title: '买咖啡豆',
    description: '',
    notes: '',
    done: false,
    skipped: false,
    startDate: null,
    startTime: null,
    dueDate: addDays(today, 3),
    dueTime: null,
    estimatedMinutes: 10,
    actualMinutes: null,
    cognitiveLoad: 'low',
    repeat: NO_REPEAT,
    tags: ['生活'],
    order: 6,
    completedAt: null,
  },
  {
    id: 8,
    title: '每周复盘',
    description: '回顾完成率，决定下周任务量。',
    notes: '',
    done: false,
    skipped: false,
    startDate: null,
    startTime: null,
    dueDate: addDays(today, 6),
    dueTime: '20:00',
    estimatedMinutes: 20,
    actualMinutes: null,
    cognitiveLoad: 'medium',
    repeat: { freq: 'weekly', interval: 1, end: 'never', until: null, count: null },
    tags: ['复盘'],
    order: 7,
    completedAt: null,
  },
];

/** A few past days so streak / weekly report have something to show. */
export const mockCompletions: Completion[] = [
  { id: 1, taskId: 1, date: daysAgoISO(0), minutes: 33 },
  { id: 2, taskId: 1, date: daysAgoISO(1), minutes: 30 },
  { id: 3, taskId: 9, date: daysAgoISO(1), minutes: 25 },
  { id: 4, taskId: 1, date: daysAgoISO(2), minutes: 31 },
  { id: 5, taskId: 1, date: daysAgoISO(3), minutes: 28 },
  { id: 6, taskId: 1, date: daysAgoISO(6), minutes: 30 },
];

/** Feedback samples feeding avg stress / energy in the insight panel. */
export const mockFeedback: FeedbackSample[] = [
  { date: daysAgoISO(0), stress_level: 6, energy_level: 5 },
  { date: daysAgoISO(1), stress_level: 7, energy_level: 4 },
  { date: daysAgoISO(2), stress_level: 5, energy_level: 6 },
  { date: daysAgoISO(3), stress_level: 8, energy_level: 3 },
];

export const mockWhyNow = '昨天你只完成了 3/5，所以今天先排轻一点。这件事在 15:00 前做完就好。';
