import { useCallback, useMemo, useState } from 'react';

import { dataSource } from '@/api/config';
import type { InsightRead, UserRead } from '@/api/types';
import {
  energyLabel,
  mockCompletions,
  mockFeedback,
  mockGoals,
  mockPlanChanges,
  mockPlanId,
  mockTasks,
  mockUser,
} from '@/data/mock';
import { addDays, todayISO } from '@/domain/date';
import {
  decomposePending as decomposePendingLocal,
  type DraftTask,
  type PendingTask,
} from '@/domain/decompose';
import type { Goal } from '@/domain/goal';
import { buildInsight } from '@/domain/insight';
import { type SchedulingPreferences } from '@/domain/preferences';
import { buildLists, buildRuler, countLists, pickCurrentTask } from '@/domain/selectors';
import { buildSituation } from '@/domain/situation';
import {
  completionRate,
  completedToday,
  currentStreak,
  dailyBuckets,
  longestStreak,
  monthlyBuckets,
} from '@/domain/stats';
import { isClosed, seriesTasks, type Task } from '@/domain/task';
import * as ops from '@/domain/task-ops';
import type { NewTaskInput } from '@/domain/task-ops';
import { ApiPlanProvider } from '@/state/api-plan';
import {
  PlanContext,
  type Assessment,
  type FeedbackInput,
  type FeedbackResult,
  type PendingTaskInput,
  type PlanContextValue,
  type SchedulingActionResult,
} from '@/state/plan-context';
import { loadPreferences, savePreferences } from '@/state/preferences-store';


const initialStore: ops.StoreState = {
  tasks: mockTasks,
  completions: mockCompletions,
  focusSessions: [],
};

function MockPlanProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ops.StoreState>(initialStore);
  const [assessment, setAssessment] = useState<Assessment>({ energy: 5, mood: 3, stress: 4 });
  const [goals, setGoals] = useState<Goal[]>(mockGoals);
  const [pendingTasks, setPendingTasks] = useState<PendingTask[]>([]);
  const [preferences, setPreferences] = useState<SchedulingPreferences>(() => loadPreferences());
  const [actionError, setActionError] = useState<string | null>(null);
  const [lastConfirmedPlanId, setLastConfirmedPlanId] = useState<number | null>(null);

  const ordered = useMemo(() => {
    const seen = new Set<number>();
    return [...state.tasks]
      .sort((a, b) => a.order - b.order)
      .filter((task) => {
        if (seen.has(task.id)) return false;
        seen.add(task.id);
        return true;
      });
  }, [state.tasks]);

  const today = todayISO();
  const lists = useMemo(() => buildLists(ordered, today), [ordered, today]);
  const listCounts = useMemo(() => countLists(lists), [lists]);
  const currentTask = useMemo(() => pickCurrentTask(ordered, today), [ordered, today]);
  const ruler = useMemo(() => buildRuler(ordered, currentTask?.id, today), [ordered, currentTask, today]);

  const stats = useMemo(() => {
    const weekStart = addDays(today, -6);
    const todayTasks = state.tasks.filter((task) => task.dueDate === today);
    const todayDone = todayTasks.filter((task) => task.done).length;
    const todayOpen = todayTasks.filter((task) => !isClosed(task)).length;
    const todayTotal = todayDone + todayOpen;
    return {
      completedToday: completedToday(state.tasks),
      openCount: state.tasks.filter((task) => !isClosed(task)).length,
      doneCount: state.tasks.filter((task) => task.done).length,
      rate: completionRate(state.tasks),
      todayDone,
      todayTotal,
      todayRate: todayTotal === 0 ? 0 : todayDone / todayTotal,
      streak: currentStreak(state.completions, today),
      longest: longestStreak(state.completions),
      weekly: dailyBuckets(state.completions, 7),
      monthly: monthlyBuckets(state.completions, 6),
      focusToday: state.focusSessions
        .filter((session) => session.date === today)
        .reduce((sum, session) => sum + session.minutes, 0),
      focusWeek: state.focusSessions
        .filter((session) => session.date >= weekStart)
        .reduce((sum, session) => sum + session.minutes, 0),
    };
  }, [state.tasks, state.completions, state.focusSessions, today]);

  const insight: InsightRead = useMemo(
    () => buildInsight(mockPlanId, ordered, mockFeedback),
    [ordered],
  );

  const situation = useMemo(
    () => buildSituation(mockFeedback, mockUser.execution_weight, stats.rate),
    [stats.rate],
  );

  const addTask = useCallback((text: string, defaults?: Partial<NewTaskInput>) => {
    setState((prev) => ops.createTaskFromText(prev, text, defaults).state);
  }, []);
  const createTask = useCallback((input: NewTaskInput) => {
    setState((prev) => ops.makeTask(prev, input).state);
  }, []);
  const updateTask = useCallback((id: number, patch: Partial<Task>) => {
    setState((prev) => ops.updateTask(prev, id, patch));
  }, []);
  const updateStandard = useCallback(
    async (taskId: number, standardId: number, completed: boolean) => {
      setState((prev) =>
        ops.updateTask(prev, taskId, {
          standards: (prev.tasks.find((task) => task.id === taskId)?.standards ?? []).map(
            (standard) => (standard.id === standardId ? { ...standard, completed } : standard),
          ),
        }),
      );
    },
    [],
  );
  const deleteTask = useCallback((id: number) => {
    setState((prev) => ops.deleteTask(prev, id));
  }, []);
  const deleteTaskSeries = useCallback(async (taskId: number) => {
    setState((prev) => {
      const task = prev.tasks.find((item) => item.id === taskId);
      if (!task) return prev;
      const ids = seriesTasks(prev.tasks, task)
        .filter((item) => !item.done)
        .map((item) => item.id);
      return ids.length > 0 ? ops.batchDelete(prev, ids) : prev;
    });
  }, []);
  const setDone = useCallback((id: number, done: boolean) => {
    setState((prev) => ops.setDone(prev, id, done));
  }, []);
  const startTask = useCallback((id: number) => {
    setState((prev) => ops.updateTask(prev, id, { startedAt: new Date().toISOString() }));
  }, []);
  const completeTask = useCallback((id: number, actualMinutes?: number | null) => {
    setState((prev) => {
      const done = ops.setDone(prev, id, true);
      return actualMinutes != null
        ? ops.updateTask(done, id, { actualMinutes: Math.round(actualMinutes) })
        : done;
    });
  }, []);
  const partialCompleteTask = useCallback(
    (id: number, _completionRate: number, actualMinutes?: number | null) => {
      if (actualMinutes == null) return;
      setState((prev) =>
        ops.updateTask(prev, id, { actualMinutes: Math.round(actualMinutes) }),
      );
    },
    [],
  );
  const toggleDone = useCallback((id: number) => {
    setState((prev) => ops.toggleDone(prev, id));
  }, []);
  const setSkipped = useCallback((id: number, skipped: boolean) => {
    setState((prev) => ops.setSkipped(prev, id, skipped));
  }, []);
  const reorder = useCallback((draggedId: number, targetId: number) => {
    setState((prev) => ops.reorder(prev, draggedId, targetId));
  }, []);
  const moveBy = useCallback((id: number, delta: number) => {
    setState((prev) => ops.moveBy(prev, id, delta));
  }, []);
  const batchSetDone = useCallback((ids: number[], done: boolean) => {
    setState((prev) => ops.batchSetDone(prev, ids, done));
  }, []);
  const batchDelete = useCallback((ids: number[]) => {
    setState((prev) => ops.batchDelete(prev, ids));
  }, []);
  const batchReschedule = useCallback((ids: number[], date: string | null) => {
    setState((prev) => ops.batchReschedule(prev, ids, date));
  }, []);
  const logFocus = useCallback((taskId: number, minutes: number) => {
    setState((prev) => ops.logFocus(prev, taskId, minutes));
  }, []);

  const addPendingTask = useCallback(
    (input: PendingTaskInput) => {
      setPendingTasks((prev) => [
        ...prev,
        {
          id: Math.max(0, ...prev.map((item) => item.id)) + 1,
          title: input.title,
          priority: input.priority,
          dueDate: input.dueDate,
          notes: input.notes,
          taskKind: input.taskKind ?? 'one_off',
          planningMode: input.planningMode,
          recurrenceFrequency: input.recurrenceFrequency ?? null,
          recurrenceInterval: input.recurrenceInterval ?? null,
          startDate: input.startDate ?? null,
          dailyTargetMinutes: input.dailyTargetMinutes ?? null,
          recurrenceWeekdays: input.recurrenceWeekdays ?? null,
          targetAmount: input.targetAmount ?? null,
          targetUnit: input.targetUnit ?? null,
        },
      ]);
    },
    [],
  );

  const updatePendingTask = useCallback((id: number, patch: Partial<PendingTask>) => {
    setPendingTasks((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }, []);

  const removePendingTask = useCallback((id: number) => {
    setPendingTasks((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const [mockPreview, setMockPreview] = useState<DraftTask[] | null>(null);
  const dismissPreview = useCallback(() => setMockPreview(null), []);

  const previewMeta = useMemo(
    () => ({
      canAdjust: true,
      adjustmentCount: 0,
      maxAdjustments: 99,
      warnings: [] as string[],
      violations: [] as string[],
      threadId: 'mock',
      estimatedTotalMinutes: (mockPreview ?? []).reduce(
        (sum, task) => sum + task.estimatedMinutes,
        0,
      ),
      dailyLimitMinutes: preferences.dailyLimitMinutes,
    }),
    [mockPreview, preferences.dailyLimitMinutes],
  );

  const decomposePreview = useCallback(async () => {
    const drafts = decomposePendingLocal(pendingTasks);
    setMockPreview(drafts);
    return drafts;
  }, [pendingTasks]);

  const adjustPreview = useCallback(
    async (feedback: string) => {
      const drafts = decomposePendingLocal(pendingTasks, feedback);
      setMockPreview(drafts);
      return { drafts, applied: false, message: null };
    },
    [pendingTasks],
  );

  const confirmPreview = useCallback(async () => {
    const tasks = mockPreview ?? decomposePendingLocal(pendingTasks);
    const bySource = new Map(pendingTasks.map((item) => [item.id, item]));
    const sourceIds = Array.from(new Set(tasks.map((task) => task.sourceId)));
    const goalIdBySource = new Map<number, number>();
    const newGoals: Goal[] = [];
    let nextGoalId = Math.max(0, ...goals.map((goal) => goal.id)) + 1;

    for (const sourceId of sourceIds) {
      const item = bySource.get(sourceId);
      if (!item) continue;
      const id = nextGoalId;
      nextGoalId += 1;
      goalIdBySource.set(sourceId, id);
      newGoals.push({
        id,
        title: item.title,
        description: item.notes,
        status: 'active',
        deadline: item.dueDate,
        estimatedMinutes: null,
        priority: item.priority,
        createdAt: new Date().toISOString(),
        taskKind: item.taskKind,
        planningMode: item.planningMode,
        recurrenceFrequency: item.recurrenceFrequency ?? null,
        recurrenceInterval: item.recurrenceInterval ?? null,
        startDate: item.startDate,
        dailyTargetMinutes: item.dailyTargetMinutes,
        recurrenceWeekdays: item.recurrenceWeekdays,
        targetAmount: item.targetAmount,
        targetUnit: item.targetUnit,
      });
    }

    setGoals((prev) => [...prev, ...newGoals]);
    setState((prev) => {
      let next = prev;
      tasks.forEach((task) => {
        next = ops.makeTask(next, {
          title: task.title,
          goalId: goalIdBySource.get(task.sourceId) ?? null,
          priority: task.priority,
          dueDate: task.dueDate,
          startTime: task.startTime,
          endTime: task.endTime,
          estimatedMinutes: task.estimatedMinutes,
          taskKind: task.taskKind,
          seriesId: task.seriesId,
          seriesIndex: task.seriesIndex,
          occurrenceDate: task.occurrenceDate,
          targetAmount: task.targetAmount,
          targetUnit: task.targetUnit,
        }).state;
      });
      return next;
    });
    setPendingTasks([]);
    setMockPreview(null);
    setLastConfirmedPlanId(mockPlanId);
    return mockPlanId;
  }, [goals, pendingTasks, mockPreview]);

  const updatePreferences = useCallback(
    async (patch: Partial<SchedulingPreferences>) => {
      setActionError(null);
      setPreferences((prev) => {
        const next = { ...prev, ...patch };
        savePreferences(next);
        return next;
      });
    },
    [],
  );

  const submitFeedback = useCallback(
    async (_input: FeedbackInput): Promise<FeedbackResult> => ({
      replanTriggered: false,
      replanPlanId: null,
      cooldownMessage: null,
      saved: true,
      mode: 'recorded',
      route: 'none',
      reasons: [],
      replanError: null,
    }),
    [],
  );

  const scheduleUnavailable = useCallback(async (): Promise<SchedulingActionResult> => {
    const message = '演示模式：任务池和顺延需要连接后端。';
    setActionError(message);
    return { ok: false, message };
  }, []);

  const value = useMemo<PlanContextValue>(
    () => ({
      mode: 'mock',
      canEditTasks: true,
      canCreateTasks: true,
      loading: false,
      error: null,
      actionError,
      clearActionError: () => setActionError(null),
      refresh: () => undefined,
      retryConnection: () => undefined,
      user: mockUser as UserRead,
      tasks: ordered,
      energy: 'medium',
      energyLabelText: energyLabel.medium,
      lists,
      listCounts,
      currentTask,
      ruler,
      stats,
      insight,
      completions: state.completions,
      situation,
      preferences,
      updatePreferences,
      planChanges: mockPlanChanges,
      lastConfirmedPlanId,
      clearLastConfirmed: () => setLastConfirmedPlanId(null),
      replanNow: async () => '演示模式：重排需要连接后端。',
      feedbackHistory: [],
      refreshFeedbackHistory: async () => undefined,
      feedbackObligations: [],
      refreshFeedbackObligations: async () => undefined,
      backlogTasks: [],
      moveTask: scheduleUnavailable,
      moveTaskToBacklog: scheduleUnavailable,
      localReschedule: scheduleUnavailable,
      goals,
      pendingTasks,
      addPendingTask,
      updatePendingTask,
      removePendingTask,
      decomposePreview,
      adjustPreview,
      confirmPreview,
      previewMeta,
      previewTasks: mockPreview,
      previewBusy: false,
      dismissPreview,
      clarification: null,
      submitClarifications: () => undefined,
      dismissClarification: () => undefined,
      assessment,
      setAssessment,
      submitFeedback,
      updateWeight: async () => undefined,
      addTask,
      createTask,
      updateTask,
      updateStandard,
      deleteTask,
      deleteTaskSeries,
      setDone,
      startTask,
      completeTask,
      partialCompleteTask,
      toggleDone,
      setSkipped,
      reorder,
      moveBy,
      batchSetDone,
      batchDelete,
      batchReschedule,
      logFocus,
    }),
    [
      ordered,
      lists,
      listCounts,
      currentTask,
      ruler,
      stats,
      insight,
      state.completions,
      situation,
      preferences,
      updatePreferences,
      actionError,
      lastConfirmedPlanId,
      goals,
      pendingTasks,
      addPendingTask,
      updatePendingTask,
      removePendingTask,
      decomposePreview,
      adjustPreview,
      confirmPreview,
      previewMeta,
      mockPreview,
      dismissPreview,
      assessment,
      submitFeedback,
      scheduleUnavailable,
      addTask,
      createTask,
      updateTask,
      updateStandard,
      deleteTask,
      deleteTaskSeries,
      setDone,
      startTask,
      completeTask,
      partialCompleteTask,
      toggleDone,
      setSkipped,
      reorder,
      moveBy,
      batchSetDone,
      batchDelete,
      batchReschedule,
      logFocus,
    ],
  );

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}

export function PlanProvider({ children }: { children: React.ReactNode }) {
  if (dataSource === 'api') return <ApiPlanProvider>{children}</ApiPlanProvider>;
  return <MockPlanProvider>{children}</MockPlanProvider>;
}

export { usePlan } from '@/state/plan-context';
export type { SmartListKey } from '@/state/plan-context';
