import { createContext, useContext } from 'react';

import type { InsightRead, UserRead } from '@/api/types';
import type { DraftTask, PendingTask } from '@/domain/decompose';
import type { Goal } from '@/domain/goal';
import type { PlanChange } from '@/domain/plan-change';
import type { SchedulingPreferences } from '@/domain/preferences';
import type { RulerSegmentState, SmartListKey } from '@/domain/selectors';
import type { Situation } from '@/domain/situation';
import type { Completion } from '@/domain/stats';
import type { NewTaskInput, StoreState } from '@/domain/task-ops';
import type { Task } from '@/domain/task';

export type { SmartListKey };

export type DataMode = 'mock' | 'api';

export type Assessment = { energy: number; mood: number; stress: number };

export type FeedbackInput = {
  completionRate: number;
  freeText?: string;
  delayReason?: string;
};

export type FeedbackResult = {
  replanTriggered: boolean;
  replanPlanId: number | null;
  /** Human-readable cooldown note when a replan was requested but not eligible. */
  cooldownMessage: string | null;
};

export type PendingTaskInput = {
  title: string;
  priority: number;
  dueDate: string | null;
  notes: string;
};

export type PlanContextValue = {
  mode: DataMode;
  /** False in api mode, where the backend cannot create/edit/delete/reorder tasks. */
  canEditTasks: boolean;
  loading: boolean;
  error: string | null;
  refresh: () => void;

  user: UserRead;
  tasks: Task[];
  energy: 'low' | 'medium' | 'high';
  energyLabelText: string;
  lists: Record<SmartListKey, Task[]>;
  listCounts: Record<SmartListKey, number>;
  currentTask: Task | null;
  ruler: { key: string; state: RulerSegmentState }[];
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
  insight: InsightRead;
  completions: Completion[];

  /** Current 精力 / 压力 / 效能 + trend (see domain/situation.ts). */
  situation: Situation;
  /** Scheduling preferences, set once and reused by every generate call. */
  preferences: SchedulingPreferences;
  updatePreferences: (patch: Partial<SchedulingPreferences>) => Promise<void>;
  /** Replan change notice; mock until the backend exposes it. */
  planChanges: PlanChange[];

  /** Goals from the active plan — used only as group labels in 待办. */
  goals: Goal[];

  /** GOAL page: items waiting to be decomposed. */
  pendingTasks: PendingTask[];
  addPendingTask: (input: PendingTaskInput) => void;
  updatePendingTask: (id: number, patch: Partial<PendingTask>) => void;
  removePendingTask: (id: number) => void;
  /** Build the preview (optionally reshaped by the user's feedback). */
  decomposePending: (feedback?: string) => DraftTask[];
  /** Persist a confirmed preview. */
  confirmDecompose: (tasks: DraftTask[]) => Promise<void>;

  assessment: Assessment;
  setAssessment: (next: Assessment) => void;
  submitFeedback: (input: FeedbackInput) => Promise<FeedbackResult>;
  /** mock: adds a task; api: generates a new plan version from a goal title. */
  submitGoal: (title: string) => void;
  /** api: PATCH /users/me; mock: no-op. */
  updateWeight: (value: number) => Promise<void>;

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

export const PlanContext = createContext<PlanContextValue | null>(null);

export function usePlan(): PlanContextValue {
  const context = useContext(PlanContext);
  if (!context) throw new Error('usePlan must be used inside <PlanProvider>');
  return context;
}

export type { StoreState, Task };
