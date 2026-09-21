import { useCallback, useMemo, useState } from 'react';

import { dataSource } from '@/api/config';
import type { InsightRead, UserRead } from '@/api/types';
import { energyLabel, mockCompletions, mockFeedback, mockPlanId, mockTasks, mockUser } from '@/data/mock';
import { addDays, todayISO } from '@/domain/date';
import { buildInsight } from '@/domain/insight';
import { buildLists, buildRuler, countLists, pickCurrentTask } from '@/domain/selectors';
import {
  completionRate,
  completedToday,
  currentStreak,
  dailyBuckets,
  longestStreak,
  monthlyBuckets,
} from '@/domain/stats';
import { isClosed, type Task } from '@/domain/task';
import * as ops from '@/domain/task-ops';
import type { NewTaskInput } from '@/domain/task-ops';
import { ApiPlanProvider } from '@/state/api-plan';
import {
  PlanContext,
  type Assessment,
  type FeedbackInput,
  type FeedbackResult,
  type PlanContextValue,
} from '@/state/plan-context';
import { SessionProvider } from '@/state/session';

const initialStore: ops.StoreState = {
  tasks: mockTasks,
  completions: mockCompletions,
  focusSessions: [],
};

function MockPlanProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ops.StoreState>(initialStore);
  const [assessment, setAssessment] = useState<Assessment>({ energy: 1, mood: 2, stress: 1 });

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
    return {
      completedToday: completedToday(state.tasks),
      openCount: state.tasks.filter((task) => !isClosed(task)).length,
      doneCount: state.tasks.filter((task) => task.done).length,
      rate: completionRate(state.tasks),
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

  const addTask = useCallback((text: string, defaults?: Partial<NewTaskInput>) => {
    setState((prev) => ops.createTaskFromText(prev, text, defaults).state);
  }, []);
  const createTask = useCallback((input: NewTaskInput) => {
    setState((prev) => ops.makeTask(prev, input).state);
  }, []);
  const updateTask = useCallback((id: number, patch: Partial<Task>) => {
    setState((prev) => ops.updateTask(prev, id, patch));
  }, []);
  const deleteTask = useCallback((id: number) => {
    setState((prev) => ops.deleteTask(prev, id));
  }, []);
  const setDone = useCallback((id: number, done: boolean) => {
    setState((prev) => ops.setDone(prev, id, done));
  }, []);
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

  const submitFeedback = useCallback(
    async (_input: FeedbackInput): Promise<FeedbackResult> => ({
      replanTriggered: false,
      replanPlanId: null,
      cooldownMessage: null,
    }),
    [],
  );

  const value = useMemo<PlanContextValue>(
    () => ({
      mode: 'mock',
      canEditTasks: true,
      loading: false,
      error: null,
      refresh: () => undefined,
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
      assessment,
      setAssessment,
      submitFeedback,
      submitGoal: (title: string) => addTask(title, { dueDate: todayISO() }),
      updateWeight: async () => undefined,
      addTask,
      createTask,
      updateTask,
      deleteTask,
      setDone,
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
      assessment,
      submitFeedback,
      addTask,
      createTask,
      updateTask,
      deleteTask,
      setDone,
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
  if (dataSource === 'api') {
    return (
      <SessionProvider>
        <ApiPlanProvider>{children}</ApiPlanProvider>
      </SessionProvider>
    );
  }
  return <MockPlanProvider>{children}</MockPlanProvider>;
}

export { usePlan } from '@/state/plan-context';
export type { SmartListKey } from '@/state/plan-context';
