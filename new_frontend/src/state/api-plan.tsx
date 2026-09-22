import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { isApiError } from '@/api/client';
import {
  confirmPreview as confirmPreviewApi,
  createGoal,
  deleteGoal,
  generatePlan,
  getInsights,
  getPlan,
  getPlanChanges,
  getSituationTrends,
  listFeedback,
  listGoals,
  listPlans,
  patchTask,
  replan as replanApi,
  replanEligibility,
  runJob,
  submitAdjustPreview,
  submitFeedback as submitFeedbackApi,
  submitPreview,
  updateMe,
} from '@/api/endpoints';
import {
  patchDone,
  patchSkipped,
  pendingTaskFromGoal,
  planChangeFromApi,
  previewToDrafts,
  situationFromTrends,
  taskFromApi,
} from '@/api/mapper';
import type {
  AdjustResponse,
  FeedbackRead,
  InsightRead,
  PlanGenerateRequest,
  PlanRead,
  PreviewResponse,
  SituationTrendRead,
  UserRead,
} from '@/api/types';
import { addDays, todayISO } from '@/domain/date';
import type { PendingTask } from '@/domain/decompose';
import type { Goal } from '@/domain/goal';
import type { PlanChange } from '@/domain/plan-change';
import type { SchedulingPreferences } from '@/domain/preferences';
import { buildLists, buildRuler, countLists, pickCurrentTask } from '@/domain/selectors';
import { buildSituation } from '@/domain/situation';
import { isClosed, type Task } from '@/domain/task';
import * as ops from '@/domain/task-ops';
import {
  PlanContext,
  type Assessment,
  type FeedbackInput,
  type FeedbackResult,
  type PendingTaskInput,
  type PlanContextValue,
} from '@/state/plan-context';
import {
  loadPreferences,
  loadPreferencesRemote,
  savePreferencesRemote,
} from '@/state/preferences-store';
import { useSession } from '@/state/session';

const ENERGY_LEVELS: ('low' | 'medium' | 'high')[] = ['low', 'medium', 'high', 'high'];
const ENERGY_TO_SCORE = [2, 5, 7, 9];
const STRESS_TO_SCORE = [2, 5, 8, 10];

/** SSE stage name → human label for the generation progress line. */
const PREVIEW_STAGE_LABELS: Record<string, string> = {
  goal_analysis: '理解目标',
  theoretical_analysis: '理论分析',
  user_situation_analysis: '分析状态',
  plan_generation: '规划任务',
  rule_validation: '校验规则',
  plan_repair: '修补计划',
};

function previewStageLabel(stage: string): string {
  return PREVIEW_STAGE_LABELS[stage] ?? '生成中';
}

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
    data_sufficiency: null,
    drivers: null,
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
  const [goals, setGoals] = useState<Goal[]>([]);
  const [pendingTasks, setPendingTasks] = useState<PendingTask[]>([]);
  const [preferences, setPreferences] = useState<SchedulingPreferences>(() => loadPreferences());
  const [feedbackHistory, setFeedbackHistory] = useState<FeedbackRead[]>([]);
  const [planChanges, setPlanChanges] = useState<PlanChange[]>([]);
  const [situationTrend, setSituationTrend] = useState<SituationTrendRead | null>(null);
  // Negative ids mark pending items that are not (yet) persisted server-side.
  const tempIdRef = useRef(0);

  // `GET /plans/{id}/changes` — the replan notice. Callers load it whenever a
  // plan is applied (initial load, replan, feedback-triggered replan).
  const loadPlanChanges = useCallback(async (id: number | null) => {
    if (id == null) {
      setPlanChanges([]);
      return;
    }
    try {
      setPlanChanges((await getPlanChanges(id)).map(planChangeFromApi));
    } catch {
      setPlanChanges([]);
    }
  }, []);

  // 待拆解 drafts live on the backend as `draft` goals; the local list stays the
  // UI source of truth so a failed fetch never blanks the screen.
  const loadDraftGoals = useCallback(async () => {
    try {
      setPendingTasks((await listGoals('draft')).map(pendingTaskFromGoal));
    } catch {
      // Keep whatever is already in state.
    }
  }, []);

  /** Best-effort cleanup of persisted 待拆解 goals once they are no longer pending. */
  const discardDraftGoals = useCallback((ids: number[]) => {
    ids
      .filter((id) => id > 0)
      .forEach((id) => {
        void deleteGoal(id).catch(() => {
          // The local list is already cleared; nothing to surface.
        });
      });
  }, []);

  const refreshFeedbackHistory = useCallback(async () => {
    if (planId == null) {
      setFeedbackHistory([]);
      return;
    }
    try {
      setFeedbackHistory(await listFeedback(planId));
    } catch {
      setFeedbackHistory([]);
    }
  }, [planId]);

  const applyPlan = useCallback((plan: PlanRead) => {
    const mapped = plan.tasks.map(taskFromApi);
    // `PlanRead.goals` is built from this plan's tasks' `goal_id`, so mapping it
    // (instead of mock goals) is what makes goal progress line up with the real
    // tasks. Locally created drafts (negative ids) are kept across reloads.
    const planGoals: Goal[] = plan.goals.map((goal) => ({
      id: goal.id,
      title: goal.title,
      description: '',
      status:
        goal.status === 'completed' ? 'completed' : goal.status === 'draft' ? 'draft' : 'active',
      deadline: null,
      estimatedMinutes: null,
      priority: goal.priority ?? 2,
      createdAt: '',
    }));
    setPlanId(plan.id);
    setStore((prev) => ({ ...prev, tasks: mapped }));
    setGoals((prev) => [
      ...planGoals,
      ...prev.filter((goal) => goal.status === 'draft' && goal.id < 0),
    ]);
    void loadPlanChanges(plan.id);
  }, [loadPlanChanges]);

  const load = useCallback(async () => {
    try {
      const plans = await listPlans();
      const active = plans.find((item) => item.status === 'active') ?? plans[0];
      if (!active) {
        setPlanId(null);
        setStore((prev) => ({ ...prev, tasks: [] }));
        setInsight(emptyInsight(0));
        setPlanChanges([]);
        setError(null);
        setLoading(false);
        return;
      }
      const [plan, report] = await Promise.all([getPlan(active.id), getInsights(active.id)]);
      applyPlan(plan);
      setInsight(report);
      try {
        setFeedbackHistory(await listFeedback(active.id));
      } catch {
        setFeedbackHistory([]);
      }
      setError(null);
    } catch (caught) {
      setError(isApiError(caught) ? caught.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [applyPlan]);

  useEffect(() => {
    if (session.status !== 'ready') return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async fetch once the session is ready
    void load();
    void loadDraftGoals();
    // Prefer the server's stored preferences over the local cache once loaded.
    void loadPreferencesRemote().then(setPreferences);
    void getSituationTrends(14)
      .then(setSituationTrend)
      .catch(() => setSituationTrend(null));
  }, [session.status, load, loadDraftGoals]);

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

  const situation = useMemo(
    () =>
      situationTrend
        ? situationFromTrends(situationTrend)
        : // Fall back to the local derivation if the trend fetch failed.
          buildSituation([], (session.user ?? FALLBACK_USER).execution_weight, stats.rate),
    [situationTrend, session.user, stats.rate],
  );

  const addPendingTask = useCallback((input: PendingTaskInput) => {
    const tempId = -(tempIdRef.current += 1);
    setPendingTasks((prev) => [
      ...prev,
      {
        id: tempId,
        title: input.title,
        priority: input.priority,
        dueDate: input.dueDate,
        notes: input.notes,
      },
    ]);
    // Persist best-effort; swap the temp id for the real one so a later remove
    // can delete it. A failure leaves the item local-only.
    void createGoal({
      title: input.title,
      description: input.notes || null,
      status: 'draft',
      deadline: input.dueDate ? `${input.dueDate}T00:00:00` : null,
      priority: input.priority,
    })
      .then((goal) => {
        setPendingTasks((prev) =>
          prev.map((item) => (item.id === tempId ? { ...item, id: goal.id } : item)),
        );
      })
      .catch(() => {
        // Draft persistence is best-effort; the local item still renders.
      });
  }, []);

  const updatePendingTask = useCallback((id: number, patch: Partial<PendingTask>) => {
    setPendingTasks((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }, []);

  const removePendingTask = useCallback((id: number) => {
    setPendingTasks((prev) => prev.filter((item) => item.id !== id));
    if (id > 0) {
      void deleteGoal(id).catch(() => {
        // Best-effort; the local list is already correct.
      });
    }
  }, []);

  const [previewThread, setPreviewThread] = useState<string | null>(null);
  const [previewMeta, setPreviewMeta] = useState<PlanContextValue['previewMeta']>(null);
  const [previewStage, setPreviewStage] = useState<string | null>(null);

  // While a generation job is streaming, `previewStage` carries the current
  // stage label; fold it into `previewMeta` so consumers only read one field.
  const effectivePreviewMeta = useMemo<PlanContextValue['previewMeta']>(() => {
    if (previewStage == null) return previewMeta;
    return {
      canAdjust: previewMeta?.canAdjust ?? true,
      adjustmentCount: previewMeta?.adjustmentCount ?? 0,
      maxAdjustments: previewMeta?.maxAdjustments ?? 0,
      warnings: previewMeta?.warnings ?? [],
      stage: previewStage,
    };
  }, [previewMeta, previewStage]);

  const buildGenerateRequest = useCallback(
    (): PlanGenerateRequest => ({
      goals: pendingTasks.map((item) => ({
        title: item.title,
        description: item.notes || undefined,
        priority: item.priority,
        deadline: item.dueDate ? `${item.dueDate}T00:00:00` : null,
      })),
      plan_title: pendingTasks[0]?.title ?? '新计划',
      available_minutes_per_day: preferences.availableMinutesPerDay,
      daily_limit_minutes: preferences.dailyLimitMinutes,
      buffer_minutes: preferences.bufferMinutes,
      high_cognitive_max_per_day: preferences.highCognitiveMaxPerDay,
    }),
    [pendingTasks, preferences],
  );

  // 拆解现在真的走后端：`preview`（不落库）→ `adjust`（带反馈重来）→ `confirm`（落库）。
  // 两个生成接口都立刻返回 job 描述，实际工作在 SSE 上流式完成（`runJob`）。
  const onPreviewStage = useCallback((stage: string) => {
    setPreviewStage(previewStageLabel(stage));
  }, []);

  const decomposePreview = useCallback(async () => {
    // NOTE: do NOT toggle the global `loading` here. `_layout` renders a
    // full-screen "正在连接后端…" while it is true, which unmounts the goal
    // screen and looks like "点击就断开后端". The screen owns its own busy flag.
    try {
      const job = await submitPreview(buildGenerateRequest());
      const status = await runJob(job, onPreviewStage);
      const response = status.result as unknown as PreviewResponse | null;
      if (!response?.preview) {
        setError(status.error ?? '拆解没有返回结果，请重试。');
        setPreviewThread(null);
        setPreviewMeta(null);
        return [];
      }
      setPreviewThread(response.thread_id);
      setPreviewMeta({
        canAdjust: response.preview.can_adjust,
        adjustmentCount: response.preview.adjustment_count,
        maxAdjustments: response.preview.max_adjustments,
        warnings: response.warnings,
      });
      setError(null);
      return previewToDrafts(response.preview.tasks);
    } catch (caught) {
      setError(isApiError(caught) ? caught.message : '拆解失败');
      setPreviewThread(null);
      setPreviewMeta(null);
      return [];
    } finally {
      setPreviewStage(null);
    }
  }, [buildGenerateRequest, onPreviewStage]);

  const adjustPreview = useCallback(
    async (feedback: string) => {
      if (!previewThread) {
        return { drafts: null, applied: false, message: '预览已失效，请重新拆解。' };
      }
      try {
        const job = await submitAdjustPreview(previewThread, feedback);
        const status = await runJob(job, onPreviewStage);
        const response = status.result as unknown as AdjustResponse;
        // 预算耗尽时后端会直接给最终计划：应用它并关掉预览。
        if (response.final_plan) {
          discardDraftGoals(pendingTasks.map((item) => item.id));
          applyPlan(response.final_plan);
          setPendingTasks([]);
          setPreviewThread(null);
          setPreviewMeta(null);
          return { drafts: null, applied: true, message: '调整次数已用完，已直接生成计划。' };
        }
        if (response.preview) {
          setPreviewMeta({
            canAdjust: response.preview.can_adjust,
            adjustmentCount: response.preview.adjustment_count,
            maxAdjustments: response.preview.max_adjustments,
            warnings: response.warnings,
          });
          return {
            drafts: previewToDrafts(response.preview.tasks),
            applied: false,
            message: response.budget_exhausted ? '调整次数已用完。' : null,
          };
        }
        return { drafts: null, applied: false, message: '这次没有返回新的预览。' };
      } catch (caught) {
        setError(isApiError(caught) ? caught.message : '重新生成失败');
        return { drafts: null, applied: false, message: '重新生成失败。' };
      } finally {
        setPreviewStage(null);
      }
    },
    [previewThread, applyPlan, onPreviewStage, pendingTasks, discardDraftGoals],
  );

  const confirmPreview = useCallback(async () => {
    if (!previewThread) return;
    try {
      const response = await confirmPreviewApi(previewThread);
      discardDraftGoals(pendingTasks.map((item) => item.id));
      applyPlan(response.plan);
      setPendingTasks([]);
      setPreviewThread(null);
      setPreviewMeta(null);
      setError(null);
    } catch (caught) {
      setError(isApiError(caught) ? caught.message : '确认失败');
    }
  }, [previewThread, applyPlan, pendingTasks, discardDraftGoals]);

  /** 手动重排：先查冷却，可用则生成新版本并切过去。返回一句给用户看的结果。 */
  const replanNow = useCallback(async () => {
    if (planId == null) return '还没有计划，先去「目标」拆一个。';
    try {
      const eligibility = await replanEligibility(planId);
      if (!eligibility.eligible) {
        return eligibility.next_eligible_at
          ? `重排冷却中，最早 ${eligibility.next_eligible_at.slice(0, 16).replace('T', ' ')} 可以再排。`
          : '当前还不能重排。';
      }
      const result = await replanApi(planId, { trigger_type: 'manual', reason: 'user requested' });
      const [plan, report] = await Promise.all([
        getPlan(result.plan_id),
        getInsights(result.plan_id),
      ]);
      applyPlan(plan);
      setInsight(report);
      try {
        setFeedbackHistory(await listFeedback(result.plan_id));
      } catch {
        setFeedbackHistory([]);
      }
      setError(null);
      return `已生成新一版计划（v${result.new_version}），调整了 ${result.changed_task_ids.length} 个任务。`;
    } catch (caught) {
      const message = isApiError(caught) ? caught.message : '重排失败';
      setError(message);
      return message;
    }
  }, [planId, applyPlan]);

  const updatePreferences = useCallback(
    async (patch: Partial<SchedulingPreferences>) => {
      const next = { ...preferences, ...patch };
      setPreferences(next);
      // Updates the offline cache and write-throughs to the API (api mode).
      await savePreferencesRemote(next);
    },
    [preferences],
  );

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
        try {
          setFeedbackHistory(await listFeedback(response.replan_plan_id));
        } catch {
          setFeedbackHistory([]);
        }
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
      situation,
      preferences,
      updatePreferences,
      planChanges,
      replanNow,
      feedbackHistory,
      refreshFeedbackHistory,
      goals,
      pendingTasks,
      addPendingTask,
      updatePendingTask,
      removePendingTask,
      decomposePreview,
      adjustPreview,
      confirmPreview,
      previewMeta: effectivePreviewMeta,
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
    situation,
    preferences,
    updatePreferences,
    planChanges,
    goals,
    pendingTasks,
    addPendingTask,
    updatePendingTask,
    removePendingTask,
    decomposePreview,
    adjustPreview,
    confirmPreview,
    effectivePreviewMeta,
    assessment,
    submitFeedback,
    replanNow,
    feedbackHistory,
    refreshFeedbackHistory,
    submitGoal,
    updateWeight,
    setDone,
    toggleDone,
    setSkipped,
    logFocus,
  ]);

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}
