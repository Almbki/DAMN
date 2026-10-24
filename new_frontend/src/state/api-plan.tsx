import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { isApiError } from '@/api/client';
import {
  confirmPreview as confirmPreviewApi,
  createGoal,
  deleteGoal,
  deleteTask as deleteTaskApi,
  getInsights,
  getPlan,
  getPlanChanges,
  getSituationTrends,
  jobHandleFromId,
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
  updateGoal,
  updateMe,
} from '@/api/endpoints';
import {
  goalFromApi,
  patchDone,
  patchSkipped,
  pendingTaskFromGoal,
  planChangeFromApi,
  previewToDrafts,
  situationFromTrends,
  taskCompletePatch,
  taskFromApi,
  taskPartialPatch,
  taskPatchFromDomain,
  taskStartPatch,
} from '@/api/mapper';
import type {
  AdjustResponse,
  FeedbackRead,
  FeedbackReplanJobResult,
  FeedbackSubmitResponse,
  InsightRead,
  PlanGenerateRequest,
  PlanRead,
  PreviewRead,
  PreviewResponse,
  ReplanResponse,
  SituationTrendRead,
  UpdateGoalRequest,
  UserRead,
} from '@/api/types';
import { addDays, todayISO } from '@/domain/date';
import type { PendingTask } from '@/domain/decompose';
import type { Goal } from '@/domain/goal';
import type { PlanChange } from '@/domain/plan-change';
import type { SchedulingPreferences } from '@/domain/preferences';
import { buildLists, buildRuler, countLists, pickCurrentTask } from '@/domain/selectors';
import { buildSituation } from '@/domain/situation';
import { completedToday } from '@/domain/stats';
import {
  goalTypeFromTaskKind,
  isClosed,
  taskKindFromGoalType,
  type Task,
} from '@/domain/task';
import * as ops from '@/domain/task-ops';
import {
  PlanContext,
  type Assessment,
  type FeedbackInput,
  type FeedbackResult,
  type FeedbackRoute,
  type PendingTaskInput,
  type PlanContextValue,
} from '@/state/plan-context';
import {
  loadPreferences,
  loadPreferencesRemote,
  savePreferencesRemote,
} from '@/state/preferences-store';
import { useSession } from '@/state/session';

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

function errorMessage(caught: unknown, fallback: string): string {
  if (isApiError(caught)) return caught.message;
  if (caught instanceof Error && caught.message) return caught.message;
  return fallback;
}

/** The assessment UI is a 0..10 scale; clamp to the backend's 0..10 range. */
function assessmentScore(value: number | null | undefined, fallback = 5): number {
  if (value == null || !Number.isFinite(value)) return fallback;
  return Math.min(10, Math.max(0, Math.round(value)));
}

function normalizeReplanRoute(value: string | null | undefined): FeedbackRoute | null {
  if (value === 'none' || value === 'micro_adjust' || value === 'full_replan') return value;
  return null;
}

function feedbackReasons(
  reasons: string[] | null | undefined,
  fallbackReason: string | null | undefined,
): string[] {
  if (reasons && reasons.length > 0) return reasons;
  return fallbackReason ? [fallbackReason] : [];
}

function previewMetaFrom(
  preview: PreviewRead,
  threadId: string,
  warnings: string[],
  dailyLimitMinutes: number | null,
): NonNullable<PlanContextValue['previewMeta']> {
  return {
    canAdjust: preview.can_adjust,
    adjustmentCount: preview.adjustment_count,
    maxAdjustments: preview.max_adjustments,
    warnings,
    violations: (preview.violations ?? [])
      .map((item) => item.message ?? item.code ?? item.rule ?? '')
      .filter(Boolean),
    threadId,
    estimatedTotalMinutes: preview.tasks.reduce(
      (sum, task) => sum + (task.estimated_duration || 0),
      0,
    ),
    dailyLimitMinutes,
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

  const todayTasks = tasks.filter((task) => task.dueDate === today);
  const todayDone = todayTasks.filter((task) => task.done).length;
  const todayOpen = todayTasks.filter((task) => !isClosed(task)).length;
  const todayTotal = todayDone + todayOpen;

  return {
    completedToday: completedToday(tasks),
    openCount: tasks.filter((task) => !isClosed(task)).length,
    doneCount: tasks.filter((task) => task.done).length,
    rate: insight.completion_rate,
    todayDone,
    todayTotal,
    todayRate: todayTotal === 0 ? 0 : todayDone / todayTotal,
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
  const { setUser, retry: retrySession } = session;
  const [store, setStore] = useState<ops.StoreState>(EMPTY_STORE);
  const storeRef = useRef(store);
  const [planId, setPlanId] = useState<number | null>(null);
  const [insight, setInsight] = useState<InsightRead>(() => emptyInsight(0));
  const [loading, setLoading] = useState(true);
  // `error` is reserved for a fatal initial load/session failure. Mutations use
  // `actionError` so one failed PATCH never blanks the whole app.
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<Assessment>({ energy: 5, mood: 3, stress: 4 });
  const [goals, setGoals] = useState<Goal[]>([]);
  const [pendingTasks, setPendingTasks] = useState<PendingTask[]>([]);
  const [preferences, setPreferences] = useState<SchedulingPreferences>(() => loadPreferences());
  const [feedbackHistory, setFeedbackHistory] = useState<FeedbackRead[]>([]);
  const [planChanges, setPlanChanges] = useState<PlanChange[]>([]);
  const [situationTrend, setSituationTrend] = useState<SituationTrendRead | null>(null);
  const [lastConfirmedPlanId, setLastConfirmedPlanId] = useState<number | null>(null);
  // Negative ids mark pending items that are not (yet) persisted server-side.
  const tempIdRef = useRef(0);

  /** Latest committed store, so event handlers never read a stale render closure. */
  const updateStore = useCallback((updater: (prev: ops.StoreState) => ops.StoreState) => {
    setStore((prev) => {
      const next = updater(prev);
      storeRef.current = next;
      return next;
    });
  }, []);

  useEffect(() => {
    storeRef.current = store;
  }, [store]);

  // Request generation guards `load()`: a stale response must never overwrite a
  // newer one (e.g. refresh pressed while the first fetch is still in flight).
  const requestSeqRef = useRef(0);
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      requestSeqRef.current += 1;
    };
  }, []);

  // Preferences can be edited while the remote read is in flight. Once the user
  // touches them, the late server value must not clobber the local change.
  const preferencesRef = useRef(preferences);
  const preferencesTouchedRef = useRef(false);
  const commitPreferences = useCallback((next: SchedulingPreferences) => {
    preferencesRef.current = next;
    setPreferences(next);
  }, []);

  const clearActionError = useCallback(() => setActionError(null), []);

  // 待拆解 drafts live on the backend as `draft` goals; the local list stays the
  // UI source of truth so a failed fetch never blanks the screen.
  const loadDraftGoals = useCallback(async () => {
    try {
      const goals = (await listGoals('draft')).map(pendingTaskFromGoal);
      if (mountedRef.current) setPendingTasks(goals);
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
      if (mountedRef.current) setFeedbackHistory([]);
      return;
    }
    try {
      const history = await listFeedback(planId);
      if (mountedRef.current) setFeedbackHistory(history);
    } catch {
      if (mountedRef.current) setFeedbackHistory([]);
    }
  }, [planId]);

  const refreshInsights = useCallback(async () => {
    if (planId == null) return;
    try {
      const report = await getInsights(planId);
      if (mountedRef.current) setInsight(report);
    } catch {
      // Background refresh is best-effort; the optimistic UI already updated.
    }
  }, [planId]);

  const applyPlan = useCallback(
    (plan: PlanRead) => {
      const goalById = new Map(plan.goals.map((goal) => [goal.id, goal]));
      // Older tasks may omit `task_kind`; derive it from the owning goal.
      const mapped = plan.tasks.map((raw) => {
        const task = taskFromApi(raw);
        if (raw.task_kind == null && raw.goal_id != null) {
          const goal = goalById.get(raw.goal_id);
          if (goal) task.taskKind = taskKindFromGoalType(goal.goal_type);
        }
        return task;
      });
      // `PlanRead.goals` is built from this plan's tasks' `goal_id`, so mapping it
      // (instead of mock goals) is what makes goal progress line up with the real
      // tasks. Locally created drafts (negative ids) are kept across reloads.
      const planGoals: Goal[] = plan.goals.map(goalFromApi);
      setPlanId(plan.id);
      updateStore((prev) => ({ ...prev, tasks: mapped }));
      setGoals((prev) => [
        ...planGoals,
        ...prev.filter((goal) => goal.status === 'draft' && goal.id < 0),
      ]);
    },
    [updateStore],
  );

  /**
   * Fetch everything that describes a plan version and make it the active one.
   * Used after confirm / adjust-finalise / replan / feedback-triggered replan so
   * insights, history and the change notice are never left on the old version.
   */
  const adoptPlan = useCallback(
    async (id: number) => {
      const [plan, report, history, changes] = await Promise.all([
        getPlan(id),
        getInsights(id),
        listFeedback(id).catch(() => [] as FeedbackRead[]),
        getPlanChanges(id).catch(() => []),
      ]);
      if (!mountedRef.current) return;
      applyPlan(plan);
      setInsight(report);
      setFeedbackHistory(history);
      setPlanChanges(changes.map(planChangeFromApi));
    },
    [applyPlan],
  );

  const load = useCallback(async () => {
    const seq = ++requestSeqRef.current;
    try {
      const plans = await listPlans();
      if (seq !== requestSeqRef.current) return;
      const active = plans.find((item) => item.status === 'active') ?? plans[0];
      if (!active) {
        if (seq !== requestSeqRef.current || !mountedRef.current) return;
        setPlanId(null);
        updateStore((prev) => ({ ...prev, tasks: [] }));
        setInsight(emptyInsight(0));
        setFeedbackHistory([]);
        setPlanChanges([]);
        setError(null);
        return;
      }
      const [plan, report, history, changes] = await Promise.all([
        getPlan(active.id),
        getInsights(active.id),
        listFeedback(active.id).catch(() => [] as FeedbackRead[]),
        getPlanChanges(active.id).catch(() => []),
      ]);
      if (seq !== requestSeqRef.current || !mountedRef.current) return;
      applyPlan(plan);
      setInsight(report);
      setFeedbackHistory(history);
      setPlanChanges(changes.map(planChangeFromApi));
      setError(null);
    } catch (caught) {
      if (seq !== requestSeqRef.current || !mountedRef.current) return;
      setError(errorMessage(caught, '加载失败'));
    } finally {
      if (seq === requestSeqRef.current && mountedRef.current) setLoading(false);
    }
  }, [applyPlan, updateStore]);

  useEffect(() => {
    if (session.status !== 'authenticated') return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async fetch once the session is ready
    void load();
    void loadDraftGoals();
    // Prefer the server's stored preferences over the local cache once loaded.
    void loadPreferencesRemote().then((next) => {
      if (!mountedRef.current || preferencesTouchedRef.current) return;
      commitPreferences(next);
    });
    void getSituationTrends(14)
      .then((trend) => {
        if (mountedRef.current) setSituationTrend(trend);
      })
      .catch(() => {
        if (mountedRef.current) setSituationTrend(null);
      });
  }, [session.status, load, loadDraftGoals, commitPreferences]);

  const refresh = useCallback(() => {
    setLoading(true);
    void load();
    void getSituationTrends(14)
      .then((trend) => {
        if (mountedRef.current) setSituationTrend(trend);
      })
      .catch(() => {
        if (mountedRef.current) setSituationTrend(null);
      });
  }, [load]);

  const retryConnection = useCallback(() => {
    setError(null);
    setLoading(true);
    retrySession();
    void load();
  }, [retrySession, load]);

  const clearLastConfirmed = useCallback(() => setLastConfirmedPlanId(null), []);

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

  const energy: 'low' | 'medium' | 'high' =
    (['low', 'medium', 'high', 'high'] as const)[assessment.energy] ?? 'medium';

  const situation = useMemo(
    () =>
      situationTrend
        ? situationFromTrends(situationTrend)
        : // Fall back to the local derivation if the trend fetch failed.
          buildSituation([], (session.user ?? FALLBACK_USER).execution_weight, stats.rate),
    [situationTrend, session.user, stats.rate],
  );

  const addPendingTask = useCallback(
    (input: PendingTaskInput) => {
      const tempId = -(tempIdRef.current += 1);
      setPendingTasks((prev) => [
        ...prev,
        {
          id: tempId,
          title: input.title,
          priority: input.priority,
          dueDate: input.dueDate,
          notes: input.notes,
          taskKind: input.taskKind ?? 'one_off',
          startDate: input.startDate ?? null,
          dailyTargetMinutes: input.dailyTargetMinutes ?? null,
          recurrenceWeekdays: input.recurrenceWeekdays ?? null,
          targetAmount: input.targetAmount ?? null,
          targetUnit: input.targetUnit ?? null,
        },
      ]);
      setActionError(null);
      // Persist best-effort; swap the temp id for the real one so a later remove
      // can delete it. A failure leaves the item local-only.
      void createGoal({
        title: input.title,
        description: input.notes || null,
        status: 'draft',
        deadline: input.dueDate ? `${input.dueDate}T00:00:00` : null,
        priority: input.priority,
        goal_type: goalTypeFromTaskKind(input.taskKind),
        task_kind: input.taskKind,
        start_date: input.startDate ?? null,
        daily_target_minutes: input.dailyTargetMinutes ?? null,
        recurrence_weekdays: input.recurrenceWeekdays ?? null,
        target_amount: input.targetAmount ?? null,
        target_unit: input.targetUnit ?? null,
      })
        .then((goal) => {
          if (!mountedRef.current) return;
          setPendingTasks((prev) =>
            prev.map((item) => (item.id === tempId ? { ...item, id: goal.id } : item)),
          );
        })
        .catch((caught) => {
          if (mountedRef.current) setActionError(errorMessage(caught, '保存待拆解任务失败'));
        });
    },
    [],
  );

  const updatePendingTask = useCallback((id: number, patch: Partial<PendingTask>) => {
    setPendingTasks((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
    setActionError(null);
    // Negative ids are local-only drafts.
    if (id <= 0) return;

    const body: UpdateGoalRequest = {};
    if (patch.title !== undefined) body.title = patch.title;
    if (patch.notes !== undefined) body.description = patch.notes;
    if (patch.priority !== undefined) body.priority = patch.priority;
    if (patch.dueDate !== undefined) {
      body.deadline = patch.dueDate ? `${patch.dueDate}T00:00:00` : null;
    }
    if (patch.taskKind !== undefined) body.task_kind = patch.taskKind;
    if (patch.startDate !== undefined) body.start_date = patch.startDate;
    if (patch.dailyTargetMinutes !== undefined) {
      body.daily_target_minutes = patch.dailyTargetMinutes;
    }
    if (patch.recurrenceWeekdays !== undefined) {
      body.recurrence_weekdays = patch.recurrenceWeekdays;
    }
    if (patch.targetAmount !== undefined) body.target_amount = patch.targetAmount;
    if (patch.targetUnit !== undefined) body.target_unit = patch.targetUnit;
    if (Object.keys(body).length === 0) return;
    void updateGoal(id, body).catch((caught) => {
      if (mountedRef.current) setActionError(errorMessage(caught, '保存目标失败'));
    });
  }, []);

  const removePendingTask = useCallback((id: number) => {
    setPendingTasks((prev) => prev.filter((item) => item.id !== id));
    setActionError(null);
    if (id > 0) {
      void deleteGoal(id).catch((caught) => {
        if (mountedRef.current) setActionError(errorMessage(caught, '删除目标失败'));
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
      violations: previewMeta?.violations ?? [],
      threadId: previewMeta?.threadId ?? '',
      estimatedTotalMinutes: previewMeta?.estimatedTotalMinutes ?? 0,
      dailyLimitMinutes: previewMeta?.dailyLimitMinutes ?? null,
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
        goal_type: goalTypeFromTaskKind(item.taskKind),
        task_kind: item.taskKind,
        start_date: item.startDate,
        daily_target_minutes: item.dailyTargetMinutes,
        recurrence_weekdays: item.recurrenceWeekdays,
        target_amount: item.targetAmount,
        target_unit: item.targetUnit,
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
    setActionError(null);
    try {
      const job = await submitPreview(buildGenerateRequest());
      const status = await runJob(job, onPreviewStage);
      const response = status.result as unknown as PreviewResponse | null;
      if (status.status === 'failed' || !response?.preview) {
        setActionError(status.error ?? '拆解没有返回结果，请重试。');
        setPreviewThread(null);
        setPreviewMeta(null);
        return [];
      }
      setPreviewThread(response.thread_id);
      setPreviewMeta(
        previewMetaFrom(
          response.preview,
          response.thread_id,
          response.warnings,
          preferences.dailyLimitMinutes ?? null,
        ),
      );
      return previewToDrafts(response.preview.tasks);
    } catch (caught) {
      setActionError(errorMessage(caught, '拆解失败'));
      setPreviewThread(null);
      setPreviewMeta(null);
      return [];
    } finally {
      setPreviewStage(null);
    }
  }, [buildGenerateRequest, onPreviewStage, preferences.dailyLimitMinutes]);

  const adjustPreview = useCallback(
    async (feedback: string) => {
      if (!previewThread) {
        return { drafts: null, applied: false, message: '预览已失效，请重新拆解。' };
      }
      setActionError(null);
      try {
        const job = await submitAdjustPreview(previewThread, feedback);
        const status = await runJob(job, onPreviewStage);
        if (status.status === 'failed') {
          throw new Error(status.error ?? '重新生成失败');
        }
        const response = status.result as unknown as AdjustResponse;
        // 预算耗尽时后端会直接给最终计划：应用它并关掉预览。
        if (response.final_plan) {
          discardDraftGoals(pendingTasks.map((item) => item.id));
          await adoptPlan(response.final_plan.id);
          setLastConfirmedPlanId(response.final_plan.id);
          setPendingTasks([]);
          setPreviewThread(null);
          setPreviewMeta(null);
          return { drafts: null, applied: true, message: '调整次数已用完，已直接生成计划。' };
        }
        if (response.preview) {
          setPreviewMeta(
            previewMetaFrom(
              response.preview,
              response.thread_id,
              response.warnings,
              preferences.dailyLimitMinutes ?? null,
            ),
          );
          return {
            drafts: previewToDrafts(response.preview.tasks),
            applied: false,
            message: response.budget_exhausted ? '调整次数已用完。' : null,
          };
        }
        return { drafts: null, applied: false, message: '这次没有返回新的预览。' };
      } catch (caught) {
        setActionError(errorMessage(caught, '重新生成失败'));
        return { drafts: null, applied: false, message: errorMessage(caught, '重新生成失败。') };
      } finally {
        setPreviewStage(null);
      }
    },
    [
      previewThread,
      adoptPlan,
      onPreviewStage,
      pendingTasks,
      discardDraftGoals,
      preferences.dailyLimitMinutes,
    ],
  );

  const confirmPreview = useCallback(async () => {
    if (!previewThread) return;
    setActionError(null);
    try {
      const response = await confirmPreviewApi(previewThread);
      discardDraftGoals(pendingTasks.map((item) => item.id));
      // Confirm returns the plan synchronously; adopt it fully so the todo page
      // immediately has its insight, feedback history and change notice.
      await adoptPlan(response.plan.id);
      setLastConfirmedPlanId(response.plan.id);
      setPendingTasks([]);
      setPreviewThread(null);
      setPreviewMeta(null);
    } catch (caught) {
      setActionError(errorMessage(caught, '确认失败'));
    }
  }, [previewThread, pendingTasks, discardDraftGoals, adoptPlan]);

  /** 手动重排：先查冷却，可用则生成新版本并切过去。返回一句给用户看的结果。 */
  const replanNow = useCallback(async () => {
    if (planId == null) return '还没有计划，先去「目标」拆一个。';
    setActionError(null);
    try {
      const eligibility = await replanEligibility(planId);
      if (!eligibility.eligible) {
        return eligibility.next_eligible_at
          ? `重排冷却中，最早 ${eligibility.next_eligible_at.slice(0, 16).replace('T', ' ')} 可以再排。`
          : '当前还不能重排。';
      }
      const job = await replanApi(planId, { trigger_type: 'manual', reason: 'user requested' });
      const status = await runJob(job);
      if (status.status === 'failed') throw new Error(status.error ?? '重排失败');
      const result = status.result as unknown as ReplanResponse | null;
      if (!result?.plan_id) throw new Error('重排没有返回结果，请重试。');
      await adoptPlan(result.plan_id);
      return `已生成新一版计划（v${result.new_version}），调整了 ${result.changed_task_ids.length} 个任务。`;
    } catch (caught) {
      const message = errorMessage(caught, '重排失败');
      setActionError(message);
      return message;
    }
  }, [planId, adoptPlan]);

  const updatePreferences = useCallback(
    async (patch: Partial<SchedulingPreferences>) => {
      // Functional-from-ref so several rapid stepper clicks all see the latest
      // value (a stale `preferences` closure would drop earlier clicks).
      const next = { ...preferencesRef.current, ...patch };
      preferencesTouchedRef.current = true;
      commitPreferences(next);
      setActionError(null);
      const ok = await savePreferencesRemote(next);
      if (!ok && mountedRef.current) {
        setActionError('偏好保存失败，已保留本地设置。');
      }
    },
    [commitPreferences],
  );

  const setDone = useCallback(
    (id: number, done: boolean) => {
      setActionError(null);
      const previousTask = storeRef.current.tasks.find((task) => task.id === id) ?? null;
      const previousCompletions = storeRef.current.completions.filter(
        (completion) => completion.taskId === id,
      );
      updateStore((prev) => ops.setDone(prev, id, done));
      if (planId == null) return;
      void patchTask(planId, id, patchDone(done))
        .then(async () => {
          await Promise.all([refreshInsights(), refreshFeedbackHistory()]);
        })
        .catch((caught) => {
          // Roll the optimistic flip back so the checkbox never lies.
          if (previousTask) {
            updateStore((prev) => ({
              ...prev,
              tasks: prev.tasks.map((task) => (task.id === id ? previousTask : task)),
              completions: [
                ...prev.completions.filter((completion) => completion.taskId !== id),
                ...previousCompletions,
              ],
            }));
          }
          if (mountedRef.current) setActionError(errorMessage(caught, '同步任务失败'));
        });
    },
    [planId, refreshInsights, refreshFeedbackHistory, updateStore],
  );

  const toggleDone = useCallback(
    (id: number) => {
      // Read the latest committed store instead of the render closure so two
      // quick clicks toggle twice rather than both setting `done = true`.
      const task = storeRef.current.tasks.find((item) => item.id === id);
      if (task) setDone(id, !task.done);
    },
    [setDone],
  );

  const startTask = useCallback(
    (id: number) => {
      setActionError(null);
      const now = new Date();
      const previous = storeRef.current.tasks.find((task) => task.id === id) ?? null;
      updateStore((prev) => ops.updateTask(prev, id, { startedAt: now.toISOString() }));
      if (planId == null) return;
      void patchTask(planId, id, taskStartPatch(now))
        .then(() => refreshInsights())
        .catch((caught) => {
          if (previous) updateStore((prev) => ops.updateTask(prev, id, previous));
          if (mountedRef.current) setActionError(errorMessage(caught, '记录开始时间失败'));
        });
    },
    [planId, refreshInsights, updateStore],
  );

  const completeTask = useCallback(
    (id: number, actualMinutes?: number | null, interruptionCount?: number | null) => {
      setActionError(null);
      const previous = storeRef.current.tasks.find((task) => task.id === id) ?? null;
      updateStore((prev) => {
        const done = ops.setDone(prev, id, true);
        return actualMinutes != null
          ? ops.updateTask(done, id, { actualMinutes: Math.round(actualMinutes) })
          : done;
      });
      if (planId == null) return;
      void patchTask(planId, id, taskCompletePatch(actualMinutes, interruptionCount))
        .then(async () => {
          await Promise.all([refreshInsights(), refreshFeedbackHistory()]);
        })
        .catch((caught) => {
          if (previous) updateStore((prev) => ops.updateTask(prev, id, previous));
          if (mountedRef.current) setActionError(errorMessage(caught, '同步完成记录失败'));
        });
    },
    [planId, refreshInsights, refreshFeedbackHistory, updateStore],
  );

  const partialCompleteTask = useCallback(
    (
      id: number,
      completionRate: number,
      actualMinutes?: number | null,
      interruptionCount?: number | null,
    ) => {
      setActionError(null);
      const previous = storeRef.current.tasks.find((task) => task.id === id) ?? null;
      updateStore((prev) =>
        ops.updateTask(prev, id, {
          actualMinutes:
            actualMinutes != null ? Math.round(actualMinutes) : prev.tasks.find((t) => t.id === id)?.actualMinutes,
        }),
      );
      if (planId == null) return;
      void patchTask(planId, id, taskPartialPatch(completionRate, actualMinutes, interruptionCount))
        .then(async () => {
          await Promise.all([refreshInsights(), refreshFeedbackHistory()]);
        })
        .catch((caught) => {
          if (previous) updateStore((prev) => ops.updateTask(prev, id, previous));
          if (mountedRef.current) setActionError(errorMessage(caught, '保存进度失败'));
        });
    },
    [planId, refreshInsights, refreshFeedbackHistory, updateStore],
  );

  const setSkipped = useCallback(
    (id: number, skipped: boolean) => {
      setActionError(null);
      const previousTask = storeRef.current.tasks.find((task) => task.id === id) ?? null;
      const previousCompletions = storeRef.current.completions.filter(
        (completion) => completion.taskId === id,
      );
      updateStore((prev) => ops.setSkipped(prev, id, skipped));
      if (planId == null) return;
      void patchTask(planId, id, patchSkipped())
        .then(async () => {
          await Promise.all([refreshInsights(), refreshFeedbackHistory()]);
        })
        .catch((caught) => {
          if (previousTask) {
            updateStore((prev) => ({
              ...prev,
              tasks: prev.tasks.map((task) => (task.id === id ? previousTask : task)),
              completions: [
                ...prev.completions.filter((completion) => completion.taskId !== id),
                ...previousCompletions,
              ],
            }));
          }
          if (mountedRef.current) setActionError(errorMessage(caught, '同步任务失败'));
        });
    },
    [planId, refreshInsights, refreshFeedbackHistory, updateStore],
  );

  const updateTask = useCallback(
    (id: number, patch: Partial<Task>) => {
      setActionError(null);
      const previous = storeRef.current.tasks.find((task) => task.id === id) ?? null;
      updateStore((prev) => ops.updateTask(prev, id, patch));
      if (planId == null) return;

      const body = taskPatchFromDomain(patch);
      if (Object.keys(body).length === 0) return;
      void patchTask(planId, id, body)
        .then(() => refreshInsights())
        .catch((caught) => {
          if (previous) updateStore((prev) => ops.updateTask(prev, id, previous));
          if (mountedRef.current) setActionError(errorMessage(caught, '保存任务失败'));
        });
    },
    [planId, refreshInsights, updateStore],
  );

  const updateStandard = useCallback(
    async (taskId: number, standardId: number, completed: boolean) => {
      setActionError(null);
      const previous = storeRef.current.tasks.find((task) => task.id === taskId)?.standards;
      updateStore((prev) =>
        ops.updateTask(prev, taskId, {
          standards: (prev.tasks.find((task) => task.id === taskId)?.standards ?? []).map(
            (standard) =>
              standard.id === standardId ? { ...standard, completed } : standard,
          ),
        }),
      );
      if (planId == null) return;
      try {
        await patchTask(planId, taskId, {
          standard_updates: [{ id: standardId, completed }],
        });
        await refreshInsights();
      } catch (caught) {
        if (previous) {
          updateStore((prev) => ops.updateTask(prev, taskId, { standards: previous }));
        }
        if (mountedRef.current) setActionError(errorMessage(caught, '保存子任务失败'));
      }
    },
    [planId, refreshInsights, updateStore],
  );

  const moveBy = useCallback(
    (id: number, delta: number) => {
      if (planId == null) {
        updateStore((prev) => ops.moveBy(prev, id, delta));
        return;
      }
      // The backend has no ordering endpoint: "move" means reschedule the day.
      const task = storeRef.current.tasks.find((item) => item.id === id);
      if (!task) return;
      const base = task.dueDate ?? todayISO();
      updateTask(id, { dueDate: addDays(base, delta) });
    },
    [planId, updateTask, updateStore],
  );

  // The backend records actual duration only as part of a completion execution
  // (there is no `actual_duration` task column), so a standalone focus log stays
  // local — it still feeds the local focus counters.
  const logFocus = useCallback(
    (taskId: number, minutes: number) => {
      updateStore((prev) => ops.logFocus(prev, taskId, minutes));
    },
    [updateStore],
  );

  /** Soft-delete a task optimistically; a failure restores the whole store. */
  const deleteTask = useCallback(
    (id: number) => {
      const snapshot = storeRef.current;
      setActionError(null);
      updateStore((prev) => ops.deleteTask(prev, id));
      if (planId == null) return;
      void deleteTaskApi(planId, id)
        .then(async () => {
          await Promise.all([refreshInsights(), refreshFeedbackHistory()]);
        })
        .catch((caught) => {
          updateStore(() => snapshot);
          if (mountedRef.current) setActionError(errorMessage(caught, '删除任务失败'));
        });
    },
    [planId, refreshInsights, refreshFeedbackHistory, updateStore],
  );

  const updateWeight = useCallback(
    async (weight: number) => {
      setActionError(null);
      try {
        const me = await updateMe({ execution_weight: weight });
        setUser(me);
      } catch (caught) {
        setActionError(errorMessage(caught, '更新失败'));
      }
    },
    [setUser],
  );

  const submitFeedback = useCallback(
    async (input: FeedbackInput): Promise<FeedbackResult> => {
      if (planId == null) {
        return {
          replanTriggered: false,
          replanPlanId: null,
          cooldownMessage: '还没有计划，先生成一个。',
          saved: false,
          mode: 'recorded',
          route: null,
          reasons: [],
          replanError: null,
        };
      }
      setActionError(null);

      let response: FeedbackSubmitResponse;
      try {
        // `completionRate` is today's rate supplied by the UI (todayDone /
        // (todayDone + todayOpen)), not the lifetime insight rate.
        response = await submitFeedbackApi(
          planId,
          {
            date: todayISO(),
            completion_rate: Math.max(0, Math.min(1, input.completionRate)),
            stress_level: assessmentScore(assessment.stress),
            energy_level: assessmentScore(assessment.energy),
            free_text: input.freeText ?? null,
            delay_reason: input.delayReason ?? null,
            task_reasons: input.taskReasons?.map((reason) => ({
              task_id: reason.taskId,
              reason: reason.reason,
              note: reason.note ?? null,
            })),
          },
          { streamReplan: true },
        );
      } catch (caught) {
        const message = errorMessage(caught, '反馈提交失败');
        setActionError(message);
        return {
          replanTriggered: false,
          replanPlanId: null,
          cooldownMessage: message,
          saved: false,
          mode: 'recorded',
          route: null,
          reasons: [],
          replanError: message,
        };
      }

      // The feedback row is persisted from here on. A replan failure must NEVER
      // be reported as a failed submission.
      let route = normalizeReplanRoute(response.replan_decision);
      let reasons = feedbackReasons(response.adjustment?.reasons, response.replan_reason);
      let replanPlanId = response.replan_plan_id;
      let replanError: string | null = null;

      if (response.replan_job_id) {
        try {
          // The replan graph runs as a job; its completed result is the truth.
          const status = await runJob(jobHandleFromId(response.replan_job_id));
          if (status.status === 'failed') throw new Error(status.error ?? '重排失败');
          const jobResult = status.result as FeedbackReplanJobResult | null;
          replanPlanId = jobResult?.replan_triggered ? (jobResult.replan_plan_id ?? null) : null;
          route = normalizeReplanRoute(jobResult?.replan_decision) ?? route;
          const jobReasons = feedbackReasons(
            jobResult?.adjustment?.reasons,
            jobResult?.replan_reason,
          );
          if (jobReasons.length > 0) reasons = jobReasons;
        } catch (caught) {
          replanPlanId = null;
          replanError = errorMessage(caught, '重排失败');
        }
      }

      let replanned = false;
      if (replanPlanId != null) {
        try {
          await adoptPlan(replanPlanId);
          replanned = true;
        } catch (caught) {
          replanError = errorMessage(caught, '加载新计划失败');
        }
      }

      let cooldownMessage: string | null = null;
      if (!replanned) {
        await refreshFeedbackHistory();
        const eligibility = response.replan_eligibility;
        if (eligibility && !eligibility.eligible) {
          cooldownMessage = eligibility.next_eligible_at
            ? `重排冷却中，最早 ${eligibility.next_eligible_at.slice(0, 16).replace('T', ' ')} 可以再排。`
            : '重排冷却中，暂时不能再排。';
        }
      }

      return {
        replanTriggered: replanned,
        replanPlanId: replanned ? replanPlanId : null,
        cooldownMessage,
        saved: true,
        mode: replanned ? 'replanned' : 'recorded',
        route,
        reasons,
        replanError,
      };
    },
    [planId, assessment, adoptPlan, refreshFeedbackHistory],
  );

  const value = useMemo<PlanContextValue>(() => {
    // The backend has no endpoints for these; the UI hides them in api mode.
    const unsupported = () => undefined;
    return {
      mode: 'api',
      canEditTasks: true,
      canCreateTasks: false,
      loading: loading,
      error,
      actionError,
      clearActionError,
      refresh,
      retryConnection,
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
      lastConfirmedPlanId,
      clearLastConfirmed,
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
      updateWeight,
      addTask: unsupported,
      createTask: unsupported,
      updateTask,
      updateStandard,
      deleteTask,
      setDone,
      startTask,
      completeTask,
      partialCompleteTask,
      toggleDone,
      setSkipped,
      reorder: unsupported,
      moveBy,
      batchSetDone: unsupported,
      batchDelete: unsupported,
      batchReschedule: unsupported,
      logFocus,
    } satisfies PlanContextValue;
  }, [
    loading,
    session.user,
    error,
    actionError,
    clearActionError,
    refresh,
    retryConnection,
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
    lastConfirmedPlanId,
    clearLastConfirmed,
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
    effectivePreviewMeta,
    assessment,
    submitFeedback,
    updateWeight,
    updateTask,
    updateStandard,
    deleteTask,
    setDone,
    startTask,
    completeTask,
    partialCompleteTask,
    toggleDone,
    setSkipped,
    moveBy,
    logFocus,
  ]);

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}
