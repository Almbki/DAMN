/**
 * 计划相关的**纯函数**。放这里是为了让页面只做渲染。
 */

import { parseTimeToMinutes, todayString } from '@/api/format';
import type { FullPlan } from '@/api/endpoints';
import type { CognitiveLoad, PlanStatus, TaskRead, TaskStatus } from '@/api/types';

/** 已经不需要再做的状态。 */
const CLOSED_STATUSES: readonly TaskStatus[] = ['completed', 'skipped'];

export function isTaskClosed(task: TaskRead): boolean {
  return CLOSED_STATUSES.includes(task.status);
}

/**
 * 把目标输入框里的文字拆成 `GoalCreate`。
 *
 * ## 为什么按行拆
 *
 * 后端的 `TaskRead.standards` 来自 `GoalCreate.description` 的**换行**
 * （实测：`"看课\n做例题\n做练习"` → 3 条 standard，各 40 分钟）。
 * 所以「第一行当目标，剩下的行当拆解线索」是最贴合后端的输入方式，
 * 用户多写几行不是啰嗦，是在替后端把任务切开。
 */
export function splitGoalInput(text: string): { title: string; description: string | null } {
  const lines = text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  return {
    title: lines[0] ?? '',
    description: lines.length > 1 ? lines.slice(1).join('\n') : null,
  };
}

/** 这一天的任务（按开始时间、再按 `order_index` 排）。 */
export function tasksForDate(plan: FullPlan | null, date: string = todayString()): TaskRead[] {
  if (!plan) return [];
  return plan.tasks
    .filter((task) => task.scheduled_date === date)
    .sort(compareTasks);
}

/** 还没做的任务，按计划顺序。 */
export function openTasks(plan: FullPlan | null): TaskRead[] {
  if (!plan) return [];
  return plan.tasks.filter((task) => !isTaskClosed(task)).sort(compareTasks);
}

/**
 * 「现在该做哪一件」。
 *
 * 优先级：今天还没做的 → 今天之后的最近一件。**不会**推荐已经排到过去、
 * 又没完成的那些（那属于"欠账"，而这个产品刻意不做欠账提示）；
 * 但若整个计划只剩这种任务，就退而求其次给它们，免得首页空着。
 */
export function pickCurrentTask(plan: FullPlan | null, today: string = todayString()): TaskRead | null {
  const open = openTasks(plan);
  if (open.length === 0) return null;

  const todayOpen = open.filter((task) => task.scheduled_date === today);
  if (todayOpen.length > 0) return todayOpen[0];

  const future = open.filter(
    (task) => typeof task.scheduled_date === 'string' && task.scheduled_date > today,
  );
  if (future.length > 0) return future[0];

  // 全排在过去且没完成：仍然给一件，别让首页空转
  return open[0];
}

/** 计划里一共有几件、做了几件。 */
export function progress(plan: FullPlan | null): { done: number; total: number } {
  if (!plan) return { done: 0, total: 0 };
  const done = plan.tasks.filter((task) => task.status === 'completed').length;
  return { done, total: plan.tasks.length };
}

/** 界面上显示的时长：**预测优先**，没有才回落到估时。 */
export function displayMinutes(task: TaskRead): number {
  return task.predicted_duration ?? task.estimated_duration;
}

/* ------------------------------------------------------------------ 文案 */

const PLAN_STATUS_LABELS: Record<PlanStatus, string> = {
  draft: '草稿',
  active: '进行中',
  superseded: '已被新版替代',
  completed: '已完成',
  archived: '已归档',
};

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  pending: '待安排',
  scheduled: '已排期',
  in_progress: '正在做',
  completed: '已完成',
  skipped: '这次不做',
  failed: '没做成',
};

/**
 * 认知负荷的中文说法。
 *
 * 不用「高/中/低/恢复」这种直译 —— 这个词组是给用户判断"现在顶不顶得住"用的。
 */
const LOAD_LABELS: Record<CognitiveLoad, string> = {
  high: '需要整块脑子',
  medium: '要动点脑',
  low: '不怎么费脑',
  restorative: '当休息做',
};

export function planStatusLabel(status: PlanStatus): string {
  return PLAN_STATUS_LABELS[status];
}

export function taskStatusLabel(status: TaskStatus): string {
  return TASK_STATUS_LABELS[status];
}

export function cognitiveLoadLabel(load: CognitiveLoad): string {
  return LOAD_LABELS[load];
}

/** 任务的开始时间（当天零点起的分钟数），没排时间的排最后。 */
function startMinutes(task: TaskRead): number {
  return parseTimeToMinutes(task.start_time) ?? Number.MAX_SAFE_INTEGER;
}

function compareTasks(a: TaskRead, b: TaskRead): number {
  const dateA = a.scheduled_date ?? '9999-12-31';
  const dateB = b.scheduled_date ?? '9999-12-31';
  if (dateA !== dateB) return dateA < dateB ? -1 : 1;
  const startDelta = startMinutes(a) - startMinutes(b);
  if (startDelta !== 0) return startDelta;
  return a.order_index - b.order_index;
}
