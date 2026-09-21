import type { UserRead } from '@/api/types';
import { addDays, daysAgoISO, todayISO } from '@/domain/date';
import type { Goal } from '@/domain/goal';
import type { FeedbackSample } from '@/domain/insight';
import type { PlanChange } from '@/domain/plan-change';
import type { SchedulingPreferences } from '@/domain/preferences';
import type { Completion } from '@/domain/stats';
import { NO_REPEAT, type Task } from '@/domain/task';

/**
 * Mock fixtures for the local task store. Shapes follow `domain/*`; the backend
 * contract lives separately in `api/types.ts`.
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

export const mockPreferences: SchedulingPreferences = {
  availableMinutesPerDay: 480,
  dailyLimitMinutes: 300,
  bufferMinutes: 15,
  highCognitiveMaxPerDay: 2,
  sleepStart: '23:30',
  sleepEnd: '07:30',
};

const today = todayISO();

export const mockGoals: Goal[] = [
  {
    id: 1,
    title: '恢复体能',
    description: '每周三次跑步 + 力量，先把习惯稳住。',
    status: 'active',
    deadline: addDays(today, 30),
    estimatedMinutes: 900,
    priority: 2,
    createdAt: daysAgoISO(20),
  },
  {
    id: 2,
    title: '读完跑步姿势笔记',
    description: '重点看落地方式和步频。',
    status: 'active',
    deadline: addDays(today, 7),
    estimatedMinutes: 120,
    priority: 3,
    createdAt: daysAgoISO(10),
  },
  {
    id: 3,
    title: '建立每日复盘习惯',
    description: '每天记录状态，每周做一次总结。',
    status: 'active',
    deadline: null,
    estimatedMinutes: 300,
    priority: 3,
    createdAt: daysAgoISO(30),
  },
  {
    id: 4,
    title: '完成项目汇报材料',
    description: '整理本周进展与下周计划。',
    status: 'active',
    deadline: addDays(today, 2),
    estimatedMinutes: 180,
    priority: 4,
    createdAt: daysAgoISO(5),
  },
];

export const mockTasks: Task[] = [
  {
    id: 1,
    title: '慢跑 4 公里',
    description: '轻松跑，保持能说话的配速。',
    notes: '',
    goalId: 1,
    priority: 2,
    done: true,
    skipped: false,
    startDate: null,
    startTime: '07:30',
    dueDate: today,
    dueTime: '08:00',
    endTime: '08:00',
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
    goalId: 1,
    priority: 3,
    done: false,
    skipped: false,
    startDate: null,
    startTime: '15:00',
    dueDate: today,
    dueTime: '15:00',
    endTime: '15:25',
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
    goalId: 1,
    priority: 1,
    done: true,
    skipped: false,
    startDate: null,
    startTime: '15:30',
    dueDate: today,
    dueTime: '15:30',
    endTime: '15:45',
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
    goalId: 2,
    priority: 2,
    done: false,
    skipped: false,
    startDate: null,
    startTime: null,
    dueDate: addDays(today, 1),
    dueTime: null,
    endTime: null,
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
    goalId: 3,
    priority: 1,
    done: false,
    skipped: false,
    startDate: null,
    startTime: null,
    dueDate: null,
    dueTime: null,
    endTime: null,
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
    goalId: 4,
    priority: 3,
    done: false,
    skipped: false,
    startDate: daysAgoISO(2),
    startTime: '18:00',
    dueDate: daysAgoISO(2),
    dueTime: '18:00',
    endTime: '18:45',
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
    goalId: null,
    priority: 1,
    done: false,
    skipped: false,
    startDate: null,
    startTime: null,
    dueDate: addDays(today, 3),
    dueTime: null,
    endTime: null,
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
    goalId: 3,
    priority: 2,
    done: false,
    skipped: false,
    startDate: null,
    startTime: '20:00',
    dueDate: addDays(today, 6),
    dueTime: '20:00',
    endTime: '20:20',
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

/** Feedback samples feeding avg stress / energy and the situation trend. */
export const mockFeedback: FeedbackSample[] = [
  { date: daysAgoISO(0), stress_level: 6, energy_level: 5, completion_rate: 0.6 },
  { date: daysAgoISO(1), stress_level: 7, energy_level: 4, completion_rate: 0.5 },
  { date: daysAgoISO(2), stress_level: 5, energy_level: 6, completion_rate: 0.75 },
  { date: daysAgoISO(3), stress_level: 8, energy_level: 3, completion_rate: 0.33 },
  { date: daysAgoISO(4), stress_level: 6, energy_level: 5, completion_rate: 0.6 },
  { date: daysAgoISO(5), stress_level: 4, energy_level: 7, completion_rate: 0.8 },
  { date: daysAgoISO(6), stress_level: 5, energy_level: 6, completion_rate: 0.7 },
];

/** "The system changed these future days" — mock until the API exists. */
export const mockPlanChanges: PlanChange[] = [
  {
    id: 1,
    triggerType: 'feedback_triggered',
    reason: '昨天完成率 40%，系统把未来两天调轻。',
    oldVersion: 2,
    newVersion: 3,
    createdAt: new Date().toISOString(),
    days: [
      {
        date: addDays(today, 1),
        added: 1,
        moved: 2,
        removed: 0,
        summary: '把两项高认知任务挪到下午，新增一项 10 分钟短任务。',
      },
      {
        date: addDays(today, 2),
        added: 0,
        moved: 1,
        removed: 1,
        summary: '移除一项偏重的任务，另一项顺延到本周末。',
      },
    ],
  },
];
