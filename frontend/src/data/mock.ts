import type { UserRead } from '@/api/types';
import { addDays, daysAgoISO, todayISO } from '@/domain/date';
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
    done: false,
    skipped: false,
    startDate: null,
    startTime: null,
    dueDate: today,
    dueTime: '15:10',
    estimatedMinutes: 15,
    actualMinutes: null,
    repeat: NO_REPEAT,
    tags: [],
    order: 2,
    completedAt: null,
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

export const mockWhyNow = '昨天你只完成了 3/5，所以今天先排轻一点。这件事在 15:00 前做完就好。';

/** GOAL page fixtures. Progress is a time-weighted mock value (0..1). */
export type GoalStatus = 'active' | 'draft';

export interface Goal {
  id: number;
  title: string;
  progress: number;
  dueLabel: string;
  status: GoalStatus;
}

export const mockGoals: Goal[] = [
  { id: 1, title: '完成半程马拉松', progress: 0.62, dueLabel: '11 月 8 日', status: 'active' },
  { id: 2, title: '通过高等数学期末', progress: 0.35, dueLabel: '1 月 12 日', status: 'active' },
  { id: 3, title: '整理个人作品集', progress: 0, dueLabel: '未定', status: 'draft' },
];

/** What the system changed about the future, shown on the TODO page. */
export interface PlanChange {
  id: number;
  date: string;
  text: string;
}

export const mockPlanChanges: PlanChange[] = [
  { id: 1, date: addDays(today, 1), text: '把「核心力量训练」挪到 18:00 之后' },
  { id: 2, date: addDays(today, 2), text: '「提交项目汇报材料」的预算时间减半' },
  { id: 3, date: addDays(today, 4), text: '新增「拉伸与放松」15 分钟' },
];

/** Profile page fixtures. */
export const mockProfile = {
  energy: { value: 72, level: '中等' },
  stress: { value: 34, level: '偏低' },
  performance: { value: 81, level: '不错' },
  dataDays: 12,
  attribution:
    '你连续三天在傍晚完成力量训练，完成率比上午高 22%。所以系统把这类任务排在下午，并把今天的总量压到 4 件。',
};

/** Goal breakdown flow fixtures. */
export const mockGoalDraft = {
  title: '完成半程马拉松',
  steps: [
    { title: '慢跑 5 公里', minutes: 35 },
    { title: '间歇跑 6×400 米', minutes: 40 },
    { title: '长距离 12 公里', minutes: 75 },
    { title: '赛前一周减量', minutes: 50 },
  ],
};

export type ChatRole = 'ai' | 'me';

export interface ChatMessage {
  id: number;
  role: ChatRole;
  text: string;
}

export const mockGoalChat: ChatMessage[] = [
  { id: 1, role: 'ai', text: '这个目标想什么时候完成？' },
  { id: 2, role: 'me', text: '11 月 8 日比赛，之前要跑过 12 公里。' },
  { id: 3, role: 'ai', text: '你现在每周能跑几次？我按每周三次、每次不超过 75 分钟来排。' },
];

export const mockAiReplies: string[] = [
  '好，我把这条加进草案，并把当天的总量降下来。',
  '记下了，这一段保持轻松配速，不追求速度。',
  '如果这周太挤，就先只保留长距离那一次。',
];
