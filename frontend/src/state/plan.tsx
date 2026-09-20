import { createContext, useCallback, useContext, useMemo, useState } from 'react';

import { addDays, todayISO } from '@/domain/date';
import {
  completionRate,
  completedToday,
  currentStreak,
  dailyBuckets,
  longestStreak,
  monthlyBuckets,
  type Completion,
} from '@/domain/stats';
import { isClosed, type Task } from '@/domain/task';
import * as ops from '@/domain/task-ops';
import type { NewTaskInput } from '@/domain/task-ops';
import { energyLabel, mockCompletions, mockTasks, mockUser, type EnergyLevel } from '@/data/mock';

export type SmartListKey = 'all' | 'today' | 'tomorrow' | 'upcoming' | 'overdue' | 'noDate';

const initialStore: ops.StoreState = {
  tasks: mockTasks,
  completions: mockCompletions,
  focusSessions: [],
};

type PlanContextValue = {
  user: typeof mockUser;
  tasks: Task[];
  energy: EnergyLevel;
  energyLabelText: string;
  lists: Record<SmartListKey, Task[]>;
  listCounts: Record<SmartListKey, number>;
  currentTask: Task | null;
  ruler: { key: string; state: 'done' | 'now' | 'todo' }[];
  stats: {
    completedToday: number;
    openCount: number;
    doneCount: number;
    rate: number;
    streak: number;
    longest: number;
    weekly: { date: string; count: number; minutes: number }[];
    monthly: { date: string; count: number; minutes: number }[];
    focusToday: number;
    focusWeek: number;
  };
  completions: Completion[];
  addTask: (text: string, defaults?: Partial<NewTaskInput>) => void;
  createTask: (input: NewTaskInput) => void;
  updateTask: (id: number, patch: Partial<Task>) => void;
  deleteTask: (id: number) => void;
  setDone: (id: number, done: boolean) => void;
  toggleDone: (id: number) => void;
  setSkipped: (id: number, skipped: boolean) => void;
  reorder: (draggedId: number, targetId: number) => void;
  moveBy: (id: number, delta: number) => void;
  batchSetDone: (ids: number[], done: boolean) => void;
  batchDelete: (ids: number[]) => void;
  batchReschedule: (ids: number[], date: string | null) => void;
  logFocus: (taskId: number, minutes: number) => void;
};

const PlanContext = createContext<PlanContextValue | null>(null);

export function PlanProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ops.StoreState>(initialStore);
  const [energy] = useState<EnergyLevel>('medium');

  const ordered = useMemo(
    () => [...state.tasks].sort((a, b) => a.order - b.order),
    [state.tasks],
  );

  const today = todayISO();

  const lists = useMemo(() => {
    const tomorrow = addDays(today, 1);
    const open = (task: Task) => !isClosed(task);
    return {
      all: ordered,
      today: ordered.filter((task) => task.dueDate === today),
      tomorrow: ordered.filter((task) => task.dueDate === tomorrow && open(task)),
      upcoming: ordered.filter((task) => task.dueDate && task.dueDate > tomorrow && open(task)),
      overdue: ordered.filter((task) => task.dueDate && task.dueDate < today && open(task)),
      noDate: ordered.filter((task) => !task.dueDate && open(task)),
    } satisfies Record<SmartListKey, Task[]>;
  }, [ordered, today]);

  const listCounts = useMemo(() => {
    const counts = {} as Record<SmartListKey, number>;
    (Object.keys(lists) as SmartListKey[]).forEach((key) => {
      counts[key] = lists[key].filter((task) => !isClosed(task)).length;
    });
    return counts;
  }, [lists]);

  const currentTask = useMemo(() => {
    const todayOpen = ordered.filter((task) => task.dueDate === today && !isClosed(task));
    return todayOpen[0] ?? ordered.find((task) => !isClosed(task)) ?? null;
  }, [ordered, today]);

  const ruler = useMemo(() => {
    const todays = ordered.filter((task) => task.dueDate === today);
    const base = todays.length > 0 ? todays : ordered.filter((task) => !isClosed(task));
    return base.map((task) => ({
      key: String(task.id),
      state: isClosed(task) ? ('done' as const) : task.id === currentTask?.id ? ('now' as const) : ('todo' as const),
    }));
  }, [ordered, today, currentTask]);

  const stats = useMemo(() => {
    const weekStart = addDays(today, -6);
    const focusSessions = state.focusSessions;
    return {
      completedToday: completedToday(state.tasks),
      openCount: state.tasks.filter((task) => !isClosed(task)).length,
      doneCount: state.tasks.filter((task) => task.done).length,
      rate: completionRate(state.tasks),
      streak: currentStreak(state.completions, today),
      longest: longestStreak(state.completions),
      weekly: dailyBuckets(state.completions, 7),
      monthly: monthlyBuckets(state.completions, 6),
      focusToday: focusSessions
        .filter((session) => session.date === today)
        .reduce((sum, session) => sum + session.minutes, 0),
      focusWeek: focusSessions
        .filter((session) => session.date >= weekStart)
        .reduce((sum, session) => sum + session.minutes, 0),
    };
  }, [state.tasks, state.completions, state.focusSessions, today]);

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

  const value = useMemo<PlanContextValue>(
    () => ({
      user: mockUser,
      tasks: ordered,
      energy,
      energyLabelText: energyLabel[energy],
      lists,
      listCounts,
      currentTask,
      ruler,
      stats,
      completions: state.completions,
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
      energy,
      lists,
      listCounts,
      currentTask,
      ruler,
      stats,
      state.completions,
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

export function usePlan(): PlanContextValue {
  const context = useContext(PlanContext);
  if (!context) throw new Error('usePlan must be used inside <PlanProvider>');
  return context;
}

export { energyLabel };
