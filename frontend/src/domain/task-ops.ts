import { todayISO } from '@/domain/date';
import { parseQuickAdd } from '@/domain/quick-add';
import type { Completion } from '@/domain/stats';
import { NO_REPEAT, type Repeat, type Task } from '@/domain/task';

/**
 * Pure state transitions for the local task store. No React, no side effects —
 * the provider only wires these to setState.
 */

export interface FocusSession {
  id: number;
  taskId: number;
  date: string;
  minutes: number;
}

export interface StoreState {
  tasks: Task[];
  completions: Completion[];
  focusSessions: FocusSession[];
}

export interface NewTaskInput {
  title: string;
  description?: string;
  notes?: string;
  startDate?: string | null;
  startTime?: string | null;
  dueDate?: string | null;
  dueTime?: string | null;
  estimatedMinutes?: number | null;
  repeat?: Repeat;
  tags?: string[];
}

function withOrders(tasks: Task[]): Task[] {
  return tasks.map((task, index) => ({ ...task, order: index }));
}

/**
 * Ids are derived from the data itself rather than a stored counter. A counter
 * can drift when Fast Refresh restores component state, which would let two
 * list items share an id (and therefore a React key).
 */
function nextId(items: { id: number }[]): number {
  return items.reduce((max, item) => Math.max(max, item.id), 0) + 1;
}

export function makeTask(state: StoreState, input: NewTaskInput): { state: StoreState; id: number } {
  const id = nextId(state.tasks);
  const maxOrder = state.tasks.reduce((max, task) => Math.max(max, task.order), -1);
  const task: Task = {
    id,
    title: input.title.trim() || '未命名任务',
    description: input.description ?? '',
    notes: input.notes ?? '',
    done: false,
    skipped: false,
    startDate: input.startDate ?? null,
    startTime: input.startTime ?? null,
    dueDate: input.dueDate ?? null,
    dueTime: input.dueTime ?? null,
    estimatedMinutes: input.estimatedMinutes ?? null,
    actualMinutes: null,
    repeat: input.repeat ?? NO_REPEAT,
    tags: input.tags ?? [],
    order: maxOrder + 1,
    completedAt: null,
  };
  return { state: { ...state, tasks: [...state.tasks, task] }, id };
}

export function createTaskFromText(state: StoreState, text: string, defaults?: Partial<NewTaskInput>) {
  const parsed = parseQuickAdd(text);
  return makeTask(state, {
    ...defaults,
    title: parsed.title,
    dueDate: parsed.dueDate ?? defaults?.dueDate ?? null,
    dueTime: parsed.dueTime ?? defaults?.dueTime ?? null,
  });
}

export function updateTask(state: StoreState, id: number, patch: Partial<Task>): StoreState {
  return { ...state, tasks: state.tasks.map((task) => (task.id === id ? { ...task, ...patch } : task)) };
}

export function deleteTask(state: StoreState, id: number): StoreState {
  return {
    ...state,
    tasks: withOrders(state.tasks.filter((task) => task.id !== id)),
    completions: state.completions.filter((item) => item.taskId !== id),
  };
}

function completeTask(state: StoreState, id: number): StoreState {
  const task = state.tasks.find((item) => item.id === id);
  if (!task || task.done) return state;

  const today = todayISO();
  const completion: Completion = {
    id: nextId(state.completions),
    taskId: id,
    date: today,
    minutes: task.actualMinutes ?? task.estimatedMinutes ?? 0,
  };

  // Completing always marks the task done. A repeating task keeps its rule as
  // metadata but is NOT rescheduled here — rescheduling on tap made the
  // checkbox look broken (the date moved instead of the box checking).
  const tasks = state.tasks.map((item) =>
    item.id === id ? { ...item, done: true, skipped: false, completedAt: today } : item,
  );
  return { ...state, tasks, completions: [...state.completions, completion] };
}

export function setDone(state: StoreState, id: number, done: boolean): StoreState {
  const task = state.tasks.find((item) => item.id === id);
  if (!task) return state;
  if (done) return completeTask(state, id);

  const today = todayISO();
  return {
    ...state,
    completions:
      task.done ? state.completions.filter((item) => !(item.taskId === id && item.date === today)) : state.completions,
    tasks: state.tasks.map((item) => (item.id === id ? { ...item, done: false, completedAt: null } : item)),
  };
}

export function toggleDone(state: StoreState, id: number): StoreState {
  const task = state.tasks.find((item) => item.id === id);
  if (!task) return state;
  return setDone(state, id, !task.done);
}

export function setSkipped(state: StoreState, id: number, skipped: boolean): StoreState {
  const task = state.tasks.find((item) => item.id === id);
  if (!task) return state;
  const today = todayISO();
  return {
    ...state,
    completions:
      skipped && task.done
        ? state.completions.filter((item) => !(item.taskId === id && item.date === today))
        : state.completions,
    tasks: state.tasks.map((item) =>
      item.id === id ? { ...item, skipped, done: skipped ? false : item.done, completedAt: null } : item,
    ),
  };
}

/** Move `draggedId` to sit where `targetId` currently is. */
export function reorder(state: StoreState, draggedId: number, targetId: number): StoreState {
  if (draggedId === targetId) return state;
  const ordered = [...state.tasks].sort((a, b) => a.order - b.order);
  const from = ordered.findIndex((task) => task.id === draggedId);
  const to = ordered.findIndex((task) => task.id === targetId);
  if (from === -1 || to === -1) return state;
  const [moved] = ordered.splice(from, 1);
  ordered.splice(to, 0, moved);
  return { ...state, tasks: withOrders(ordered) };
}

/** Keyboard-accessible alternative to dragging. */
export function moveBy(state: StoreState, id: number, delta: number): StoreState {
  const ordered = [...state.tasks].sort((a, b) => a.order - b.order);
  const index = ordered.findIndex((task) => task.id === id);
  const target = index + delta;
  if (index === -1 || target < 0 || target >= ordered.length) return state;
  const [moved] = ordered.splice(index, 1);
  ordered.splice(target, 0, moved);
  return { ...state, tasks: withOrders(ordered) };
}

export function batchSetDone(state: StoreState, ids: number[], done: boolean): StoreState {
  return ids.reduce((acc, id) => setDone(acc, id, done), state);
}

export function batchDelete(state: StoreState, ids: number[]): StoreState {
  const set = new Set(ids);
  return {
    ...state,
    tasks: withOrders(state.tasks.filter((task) => !set.has(task.id))),
    completions: state.completions.filter((item) => !set.has(item.taskId)),
  };
}

export function batchReschedule(state: StoreState, ids: number[], date: string | null): StoreState {
  const set = new Set(ids);
  return {
    ...state,
    tasks: state.tasks.map((task) => (set.has(task.id) ? { ...task, dueDate: date } : task)),
  };
}

export function logFocus(state: StoreState, taskId: number, minutes: number): StoreState {
  if (minutes <= 0) return state;
  const id = nextId(state.focusSessions);
  return {
    ...state,
    focusSessions: [...state.focusSessions, { id, taskId, date: todayISO(), minutes }],
    tasks: state.tasks.map((task) =>
      task.id === taskId ? { ...task, actualMinutes: (task.actualMinutes ?? 0) + minutes } : task,
    ),
  };
}
