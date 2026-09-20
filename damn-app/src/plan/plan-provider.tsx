/**
 * 计划层：**当前这一个计划**的来源。
 *
 * ## 为什么要有这一层
 *
 * 后端把计划拆成三类请求：`GET /plans`（列表）、`GET /plans/{id}`（含任务明细）、
 * `PATCH .../tasks/{id}`（改一件任务）。而界面上「现在做什么」「今天的任务」
 * 说的是**同一个计划**，各自去拉一遍会得到互相矛盾的画面（勾了任务首页没变）。
 * 所以计划状态只在这里维护，页面通过 `usePlan()` 读同一份。
 *
 * ## 冷启动怎么选计划
 *
 * 1. 先看本地记住的 `planId`（上次打开的那个）→ `GET /plans/{id}`；
 * 2. 本地没有 / 那个计划已被删 → `GET /plans` 挑一个 `active` 的（没有就第一项）；
 * 3. 一个都没有 → `plan = null`，页面显示"还没有计划，去目标页生成"。
 *
 * 注意 `PUT` 语义的东西这里都没有做：**任务改动是服务端说了算**，
 * 本地只是乐观更新 + 失败回滚。
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { ApiError, describeApiError } from '@/api/client';
import * as endpoints from '@/api/endpoints';
import { normalizePlan, type FullPlan } from '@/api/endpoints';
import { readStoredPlanId, writeStoredPlanId } from '@/api/storage';
import type { ReplanResponse, TaskRead, TaskUpdateRequest } from '@/api/types';
import { useAuthToken } from '@/session/session-provider';
import { splitGoalInput } from './selectors';

export type PlanLoadState = 'idle' | 'loading' | 'ready' | 'error';

export type PlanValue = {
  plan: FullPlan | null;
  loadState: PlanLoadState;
  /** 面向用户的中文错误（已由 `describeApiError` 翻译） */
  error: string | null;
  /** 重新拉当前计划 */
  refresh: () => Promise<void>;
  /** 生成新计划（`POST /plans/generate`），成功后成为当前计划 */
  generate: (goalText: string) => Promise<FullPlan>;
  /** 改一件任务；乐观更新，失败自动回滚并把异常抛给调用方 */
  patchTask: (taskId: number, body: TaskUpdateRequest) => Promise<TaskRead>;
  /** 快捷方式：勾选 / 取消勾选 */
  setTaskCompleted: (taskId: number, completed: boolean) => Promise<TaskRead>;
  /** 切到另一个计划版本（重排之后用） */
  switchToPlan: (planId: number) => Promise<FullPlan>;
  /** 重排（`POST /plans/{id}/replan`）→ 变成新的版本 */
  replan: (reason: string) => Promise<ReplanResponse>;
};

const PlanContext = createContext<PlanValue | null>(null);

/** `completed: true` 时后端的 `status` 会变成 `completed`（实测）。 */
function optimisticTask(task: TaskRead, body: TaskUpdateRequest): TaskRead {
  // 只搬 status 语义，别把 standard_updates 之类灌进 TaskRead
  if (body.status) return { ...task, status: body.status };
  if (body.completed === true) return { ...task, status: 'completed' };
  // 实测：completed=false 会把任务打到 `pending`（不是 `scheduled`）
  if (body.completed === false) return { ...task, status: 'pending' };
  return task;
}

export function PlanProvider({ children }: { children: ReactNode }) {
  // provider 挂在登录门内部，所以这里一定有 token
  const token = useAuthToken();

  const [plan, setPlan] = useState<FullPlan | null>(null);
  const [loadState, setLoadState] = useState<PlanLoadState>('idle');
  const [error, setError] = useState<string | null>(null);

  const adopt = useCallback(async (next: FullPlan | null) => {
    await writeStoredPlanId(next?.id ?? null);
    setPlan(next);
    setError(null);
    setLoadState('ready');
  }, []);

  const load = useCallback(async () => {
    setLoadState('loading');
    try {
      const storedId = await readStoredPlanId();

      if (storedId !== null) {
        try {
          await adopt(normalizePlan(await endpoints.getPlan(token, storedId)));
          return;
        } catch (cause) {
          // 只吞"这个计划没了"，其它错误照抛
          const gone =
            cause instanceof ApiError &&
            (cause.code === 'not_found' || cause.code === 'permission_denied');
          if (!gone) throw cause;
          await writeStoredPlanId(null);
        }
      }

      const list = await endpoints.listPlans(token);
      const target = list.find((item) => item.status === 'active') ?? list[0];
      if (!target) {
        await adopt(null);
        return;
      }
      await adopt(normalizePlan(await endpoints.getPlan(token, target.id)));
    } catch (cause) {
      setError(describeApiError(cause));
      setLoadState('error');
    }
  }, [token, adopt]);

  // 挂载即拉一次。`token` 变化（换账号）会重来 —— 登录门保证这里一定是已登录态。
  useEffect(() => {
    void load();
  }, [load]);

  const generate = useCallback(
    async (goalText: string) => {
      const { title, description } = splitGoalInput(goalText);
      if (!title) throw new ApiError(422, 'validation_error', '目标不能为空', null);

      const response = await endpoints.generatePlan(token, {
        goals: [{ title, ...(description ? { description } : {}) }],
        plan_title: title,
      });

      // 后端同步跑完，`plan` 已经内联；没内联就再取一次
      const created = response.plan
        ? normalizePlan(response.plan)
        : response.plan_id
          ? normalizePlan(await endpoints.getPlan(token, response.plan_id))
          : null;

      if (!created) {
        throw new ApiError(500, 'http_error', '后端没有返回计划内容', response);
      }

      await adopt(created);
      return created;
    },
    [token, adopt],
  );

  const patchTask = useCallback(
    async (taskId: number, body: TaskUpdateRequest) => {
      if (!plan) throw new ApiError(409, 'conflict', '还没有计划', null);

      const snapshot = plan;
      setPlan({
        ...plan,
        tasks: plan.tasks.map((task) => (task.id === taskId ? optimisticTask(task, body) : task)),
      });

      try {
        const updated = await endpoints.updateTask(token, plan.id, taskId, body);
        setPlan((current) =>
          current
            ? {
                ...current,
                tasks: current.tasks.map((task) => (task.id === updated.id ? updated : task)),
              }
            : current,
        );
        return updated;
      } catch (cause) {
        setPlan(snapshot); // 回滚
        throw cause;
      }
    },
    [plan, token],
  );

  /**
   * 勾选 / 取消勾选。
   *
   * ⚠️ 取消勾选**不能**用 `{ completed: false }`：实测这个组合会把任务打成
   * `pending`，而且**对一件已经 `completed` 的任务完全没有效果**（状态不变）。
   * 只有显式写 `status` 才能真正退回去 —— 所以这里分两种情况发不同的 body。
   */
  const setTaskCompleted = useCallback(
    (taskId: number, completed: boolean) =>
      patchTask(taskId, completed ? { completed: true } : { status: 'scheduled' }),
    [patchTask],
  );

  /** 切到指定计划（重排会生成新版本，`plan_id` 变了）。 */
  const switchToPlan = useCallback(
    async (planId: number) => {
      const next = normalizePlan(await endpoints.getPlan(token, planId));
      await adopt(next);
      return next;
    },
    [token, adopt],
  );

  const replan = useCallback(
    async (reason: string) => {
      if (!plan) throw new ApiError(409, 'conflict', '还没有计划', null);

      const result = await endpoints.replan(token, plan.id, {
        trigger_type: 'manual',
        reason,
      });
      await adopt(normalizePlan(await endpoints.getPlan(token, result.plan_id)));
      return result;
    },
    [plan, token, adopt],
  );

  const value = useMemo<PlanValue>(
    () => ({
      plan,
      loadState,
      error,
      refresh: load,
      generate,
      patchTask,
      setTaskCompleted,
      switchToPlan,
      replan,
    }),
    [plan, loadState, error, load, generate, patchTask, setTaskCompleted, switchToPlan, replan],
  );

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}

export function usePlan(): PlanValue {
  const value = useContext(PlanContext);
  if (!value) throw new Error('usePlan 必须在 <PlanProvider> 里使用');
  return value;
}
