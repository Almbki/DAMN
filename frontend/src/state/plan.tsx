import { createContext, useCallback, useContext, useMemo, useState } from 'react';

import type { TaskRead } from '@/api/types';
import { energyLabel, mockPlan, mockTasks, mockUser, type EnergyLevel } from '@/data/mock';

export type RulerState = 'done' | 'now' | 'todo';

type PlanContextValue = {
  user: typeof mockUser;
  plan: typeof mockPlan;
  tasks: TaskRead[];
  currentTask: TaskRead | null;
  energy: EnergyLevel;
  completedCount: number;
  totalCount: number;
  remainingMinutes: number;
  addGoal: (title: string) => void;
  toggleTask: (id: number) => void;
  skipTask: (id: number) => void;
  startTask: (id: number) => void;
  ruler: { key: string; state: RulerState }[];
};

const PlanContext = createContext<PlanContextValue | null>(null);

function isDone(task: TaskRead) {
  return task.status === 'completed' || task.status === 'skipped';
}

export function PlanProvider({ children }: { children: React.ReactNode }) {
  const [tasks, setTasks] = useState<TaskRead[]>(mockTasks);
  const [energy] = useState<EnergyLevel>('medium');
  const [nextId, setNextId] = useState(mockTasks.length + 1);

  const currentTask = useMemo(() => {
    const inProgress = tasks.find((task) => task.status === 'in_progress');
    return inProgress ?? tasks.find((task) => !isDone(task)) ?? null;
  }, [tasks]);

  const addGoal = useCallback(
    (title: string) => {
      const trimmed = title.trim();
      if (!trimmed) return;
      setTasks((current) => {
        const id = nextId;
        const task: TaskRead = {
          id,
          plan_id: 1,
          goal_id: null,
          title: trimmed,
          estimated_duration: 25,
          predicted_duration: 25,
          cognitive_load: 'medium',
          priority: 3,
          scheduled_date: '2026-09-20',
          start_time: null,
          end_time: null,
          status: 'scheduled',
          completion_probability: 0.7,
          standards: [],
        };
        return [...current, task];
      });
      setNextId((id) => id + 1);
    },
    [nextId],
  );

  const toggleTask = useCallback((id: number) => {
    setTasks((current) =>
      current.map((task) =>
        task.id === id
          ? {
              ...task,
              // Un-completing must go through status on the real backend:
              // PATCH { completed: false } is a no-op there.
              status: isDone(task) ? 'scheduled' : 'completed',
            }
          : task,
      ),
    );
  }, []);

  const skipTask = useCallback((id: number) => {
    setTasks((current) =>
      current.map((task) => (task.id === id ? { ...task, status: 'skipped' } : task)),
    );
  }, []);

  const startTask = useCallback((id: number) => {
    setTasks((current) =>
      current.map((task) => (task.id === id ? { ...task, status: 'in_progress' } : task)),
    );
  }, []);

  const completedCount = tasks.filter(isDone).length;
  const remainingMinutes = tasks
    .filter((task) => !isDone(task))
    .reduce((sum, task) => sum + (task.estimated_duration ?? 0), 0);

  const ruler = useMemo(
    () =>
      tasks.map((task) => ({
        key: String(task.id),
        state: isDone(task)
          ? ('done' as const)
          : task.id === currentTask?.id
            ? ('now' as const)
            : ('todo' as const),
      })),
    [tasks, currentTask],
  );

  const value = useMemo<PlanContextValue>(
    () => ({
      user: mockUser,
      plan: mockPlan,
      tasks,
      currentTask,
      energy,
      completedCount,
      totalCount: tasks.length,
      remainingMinutes,
      addGoal,
      toggleTask,
      skipTask,
      startTask,
      ruler,
    }),
    [
      tasks,
      currentTask,
      energy,
      completedCount,
      remainingMinutes,
      addGoal,
      toggleTask,
      skipTask,
      startTask,
      ruler,
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
