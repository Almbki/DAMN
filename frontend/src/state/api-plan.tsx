import { useCallback, useEffect, useMemo, useState } from 'react';

import { isApiError } from '@/api/client';
import {
  generatePlan,
  getInsights,
  getPlan,
  listPlans,
  patchTask,
  submitFeedback as submitFeedbackApi,
  updateMe,
} from '@/api/endpoints';
import { patchDone, patchSkipped, taskFromApi } from '@/api/mapper';
import type { InsightRead, PlanRead, UserRead } from '@/api/types';
import { addDays, todayISO } from '@/domain/date';
import { buildLists, buildRuler, countLists, pickCurrentTask } from '@/domain/selectors';
import { isClosed, type Task } from '@/domain/task';
import * as ops from '@/domain/task-ops';
import {
  PlanContext,
  type Assessment,
  type FeedbackInput,
  type FeedbackResult,
  type PlanContextValue,
} from '@/state/plan-context';
import { useSession } from '@/state/session';

const ENERGY_LEVELS: ('low' | 'medium' | 'high')[] = ['low', 'medium', 'high', 'high'];
const ENERGY_TO_SCORE = [2, 5, 7, 9];
const STRESS_TO_SCORE = [2, 5, 8, 10];

const FALLBACK_USER: UserRead = {
  id: 0,
  email: 'demo@damn.app',
  display_name: '演示用户',
  execution_weight: 0.5,
  profile: {},
  created_at: new Date().toISOString(),
};

const EMPTY_STORE: ops.StoreState = { tasks: [], completions: [], focusSessions: [] };

function emptyInsight(planId: number): InsightRead {
  return {
    plan_id: planId,
    total_tasks: 0,
    completed_tasks: 0,
    completion_rate: 0,
    total_planned_minutes: 0,
    total_actual_minutes: 0,
    avg_stress: null,
    avg_energy: null,
    high_cognitive_minutes: 0,
    predicted_vs_actual_ratio: null,
    cognitive_load_breakdown: {},
    daily: [],
    recommendations: [],
  };
}

function statsFromInsight(
  insight: InsightRead,
  tasks: Task[],
  focusSessions: ops.FocusSession[],
  today: string,
) {
  const weekStart = addDays(today, -6);
  const dayMap = new Map(insight.daily.map((day) => [day.date, day]));
  const weekly: { date: string; count: number; minutes: number }[] = [];
  for (let offset = 6; offset >= 0; offset -= 1) {
    const date = addDays(today, -offset);
    const day = dayMap.get(date);
    weekly.push({ date, count: day?.completed_tasks ?? 0, minutes: day?.planned_minutes ?? 0 });
  }

  const monthMap = new Map<string, number>();
  insight.daily.forEach((day) => {
    const month = day.date.slice(0, 7);
    monthMap.set(month, (monthMap.get(month) ?? 0) + day.completed_tasks);
  });
  const monthly = Array.from(monthMap.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-6)
    .map(([date, count]) => ({ date, count, minutes: 0 }));

  const doneDays = new Set(insight.daily.filter((day) => day.completed_tasks > 0).map((day) => day.date));
  let cursor = doneDays.has(today) ? today : addDays(today, -1);
  let streak = 0;
  while (doneDays.has(cursor)) {
    streak += 1;
    cursor = addDays(cursor, -1);
  }
  const sortedDays = Array.from(doneDays).sort();
  let longest = 0;
  let run = 0;
  let previous: string | null = null;
  for (const day of sortedDays) {
    run = previous && addDays(previous, 1) === day ? run + 1 : 1;
    longest = Math.max(longest, run);
    previous = day;
  }

  return {
    completedToday: tasks.filter((task) => task.done && task.dueDate === today).length,
    openCount: tasks.filter((task) => !isClosed(task)).length,
    doneCount: tasks.filter((task) => task.done).length,
    rate: insight.completion_rate,
    streak,
    longest,
    weekly,
    monthly,
    focusToday: focusSessions
      .filter((session) => session.date === today)
      .reduce((sum, session) => sum + session.minutes, 0),
    focusWeek: focusSessions
      .filter((session) => session.date >= weekStart)
      .reduce((sum, session) => sum + session.minutes, 0),
  };
}

export function ApiPlanProvider({ children }: { children: React.ReactNode }) {
  const session = useSession();
  const { setUser } = session;
  const [store, setStore] = useState<ops.StoreState>(EMPTY_STORE);
  const [planId, setPlanId] = useState<number | null>(null);
  const [insight, setInsight] = useState<InsightRead>(() => emptyInsight(0));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<Assessment>({ energy: 1, mood: 2, stress: 1 });

  const applyPlan = useCallback((plan: PlanRead) => {
    const mapped = plan.tasks.map(taskFromApi);
    setPlanId(plan.id);
    setStore((prev) => ({ ...prev, tasks: mapped }));
  }, []);

  const load = useCallback(async () => {
    try {
      const plans = await listPlans();
      const active = plans.find((item) => item.status === 'active') ?? plans[0];
      if (!active) {
        setPlanId(null);
        setStore((prev) => ({ ...prev, tasks: [] }));
        setInsight(emptyInsight(0));
        setError(null);
        setLoading(false);
        return;
      }
      const [plan, report] = await Promise.all([getPlan(active.id), getInsights(active.id)]);
      applyPlan(plan);
      setInsight(report);
      setError(null);
    } catch (caught) {
      setError(isApiError(caught) ? caught.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [applyPlan]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async fetch once the session is ready
    if (session.status === 'ready') void load();
  }, [session.status, load]);

  const refresh = useCallback(() => {
    setLoading(true);
    void load();
  }, [load]);

  const ordered = useMemo(
    () => [...store.tasks].sort((a, b) => a.order - b.order),
    [store.tasks],
  );

  const today = todayISO();
  const lists = useMemo(() => buildLists(ordered, today), [ordered, today]);
  const listCounts = useMemo(() => countLists(lists), [lists]);
  const currentTask = useMemo(() => pickCurrentTask(ordered, today), [ordered, today]);
  const ruler = useMemo(() => buildRuler(ordered, currentTask?.id, today), [ordered, currentTask, today]);
  const stats = useMemo(
    () => statsFromInsight(insight, ordered, store.focusSessions, today),
    [insight, ordered, store.focusSessions, today],
  );

  const energy = ENERGY_LEVELS[assessment.energy] ?? 'medium';

  /** Optimistic local change, reverted by a reload if the server rejects it. */
  const mutate = useCallback(
    async (taskId: number, local: () => void, remote: () => Promise<unknown>) => {
      local();
      try {
        await remote();
      } catch (caught) {
        setError(isApiError(caught) ? caught.message : '同步失败');
        void load();
      }
    },
    [load],
  );

  const setDone = useCallback(
    (id: number, done: boolean) => {
      void mutate(
        id,
        () => setStore((prev) => ops.setDone(prev, id, done)),
        () => (planId == null ? Promise.resolve() : patchTask(planId, id, patchDone(done))),
      );
    },
    [mutate, planId],
  );
  const toggleDone = useCallback(
    (id: number) => {
      const task = store.tasks.find((item) => item.id === id);
      if (task) setDone(id, !task.done);
    },
    [store.tasks, setDone],
  );
  const setSkipped = useCallback(
    (id: number, skipped: boolean) => {
      void mutate(
        id,
        () => setStore((prev) => ops.setSkipped(prev, id, skipped)),
        () => (planId == null ? Promise.resolve() : patchTask(planId, id, patchSkipped())),
      );
    },
    [mutate, planId],
  );
  // The backend records actual duration only as part of a completion execution
  // (there is no `actual_duration` task column), so a standalone focus log stays
  // local — it still feeds the local focus counters.
  const logFocus = useCallback((taskId: number, minutes: number) => {
    setStore((prev) => ops.logFocus(prev, taskId, minutes));
  }, []);

  const submitGoal = useCallback(
    (title: string) => {
      const trimmed = title.trim();
      if (!trimmed) return;
      setLoading(true);
      void generatePlan({ goals: [{ title: trimmed }], plan_title: trimmed })
        .then((response) => {
          if (response.plan) applyPlan(response.plan);
          return planId ?? response.plan?.id ?? 0;
        })
        .then((id) => (id ? getInsights(id) : null))
        .then((report) => {
          if (report) setInsight(report);
          setError(null);
        })
        .catch((caught) => setError(isApiError(caught) ? caught.message : '生成计划失败'))
        .finally(() => setLoading(false));
    },
    [applyPlan, planId],
  );

  const updateWeight = useCallback(
    async (weight: number) => {
      try {
        const me = await updateMe({ execution_weight: weight });
        setUser(me);
      } catch (caught) {
        setError(isApiError(caught) ? caught.message : '更新失败');
      }
    },
    [setUser],
  );

  const submitFeedback = useCallback(
    async (input: FeedbackInput): Promise<FeedbackResult> => {
      if (planId == null) {
        return { replanTriggered: false, replanPlanId: null, cooldownMessage: '还没有计划，先生成一个。' };
      }
      const response = await submitFeedbackApi(planId, {
        date: todayISO(),
        completion_rate: Math.max(0, Math.min(1, input.completionRate)),
        stress_level: STRESS_TO_SCORE[assessment.stress] ?? 5,
        energy_level: ENERGY_TO_SCORE[assessment.energy] ?? 5,
        free_text: input.freeText ?? null,
        delay_reason: input.delayReason ?? null,
      });

      let cooldownMessage: string | null = null;
      if (response.replan_triggered && response.replan_plan_id) {
        const [plan, report] = await Promise.all([
          getPlan(response.replan_plan_id),
          getInsights(response.replan_plan_id),
        ]);
        applyPlan(plan);
        setInsight(report);
      } else if (response.replan_eligibility && !response.replan_eligibility.eligible) {
        cooldownMessage = response.replan_eligibility.next_eligible_at
          ? `重排冷却中，最早 ${response.replan_eligibility.next_eligible_at.slice(0, 16).replace('T', ' ')} 可以再排。`
          : '重排冷却中，暂时不能再排。';
      }

      return {
        replanTriggered: response.replan_triggered,
        replanPlanId: response.replan_plan_id,
        cooldownMessage,
      };
    },
    [planId, assessment, applyPlan],
  );

  const value = useMemo<PlanContextValue>(() => {
    // The backend has no endpoints for these; the UI hides them in api mode.
    const unsupported = () => undefined;
    return {
      mode: 'api',
      canEditTasks: false,
      loading: loading || session.status === 'loading',
      error: session.status === 'error' ? session.error : error,
      refresh,
      user: session.user ?? FALLBACK_USER,
      tasks: ordered,
      energy,
      energyLabelText: energy === 'low' ? '精力偏低' : energy === 'high' ? '精力不错' : '精力中等',
      lists,
      listCounts,
      currentTask,
      ruler,
      stats,
      insight,
      completions: store.completions,
      assessment,
      setAssessment,
      submitFeedback,
      submitGoal,
      updateWeight,
      addTask: unsupported,
      createTask: unsupported,
      updateTask: unsupported,
      deleteTask: unsupported,
      setDone,
      toggleDone,
      setSkipped,
      reorder: unsupported,
      moveBy: unsupported,
      batchSetDone: unsupported,
      batchDelete: unsupported,
      batchReschedule: unsupported,
      logFocus,
    } satisfies PlanContextValue;
  }, [
    loading,
    error,
    session.status,
    session.error,
    session.user,
    refresh,
    ordered,
    energy,
    lists,
    listCounts,
    currentTask,
    ruler,
    stats,
    insight,
    store.completions,
    assessment,
    submitFeedback,
    submitGoal,
    updateWeight,
    setDone,
    toggleDone,
    setSkipped,
    logFocus,
  ]);

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}
