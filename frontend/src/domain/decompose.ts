import { addDays, parseISO, todayISO } from '@/domain/date';

/**
 * Local stand-in for the backend decomposition agent. The real 拆解 (multiple
 * goals → daily tasks) is done by the backend; until that endpoint exists the
 * frontend produces an editable-preview-quality draft locally. See
 * docs/design/backend-api-gaps.md §3/§4.
 */

export interface PendingTask {
  id: number;
  title: string;
  /** 1 low · 2 medium · 3 high */
  priority: number;
  /** Deadline hint; the agent decides actual daily placement. */
  dueDate: string | null;
  notes: string;
}

export interface DraftTask {
  id: number;
  /** The `PendingTask` this candidate came from. */
  sourceId: number;
  title: string;
  dueDate: string;
  startTime: string;
  endTime: string;
  estimatedMinutes: number;
  priority: number;
}

const MORNING_SLOTS = ['09:00', '10:30', '14:00', '15:30', '16:30'];
const AFTERNOON_SLOTS = ['13:30', '15:00', '16:30', '18:00', '19:30'];

function addMinutes(time: string, minutes: number): string {
  const [h, m] = time.split(':').map(Number);
  const total = ((h * 60 + m + minutes) % 1440 + 1440) % 1440;
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}

function nextSaturday(today = todayISO()): string {
  const dow = parseISO(today).getDay();
  return addDays(today, (6 - dow + 7) % 7 || 7);
}

function splitPoints(notes: string): string[] {
  return notes
    .split(/[\n,，、;；]/)
    .map((part) => part.trim())
    .filter(Boolean);
}

/**
 * Turn the pending list into candidate daily tasks. `feedback` is the user's
 * note on the previous preview ("晚点做", "少一点", "挪到周末"…); it reshapes the
 * draft so "重新生成" visibly reacts.
 */
export function decomposePending(pending: PendingTask[], feedback = ''): DraftTask[] {
  const text = feedback.trim();
  const slots = /下午|晚点|晚上|晚一些/.test(text) ? AFTERNOON_SLOTS : MORNING_SLOTS;
  const shorter = /缩短|少一点|减少|轻一点|太多|太难/.test(text);
  const saturday = /周末|周六|周日/.test(text) ? nextSaturday() : null;
  const tomorrow = /明天/.test(text) ? addDays(todayISO(), 1) : null;
  const today = todayISO();

  const tasks: DraftTask[] = [];
  let counter = 0;

  pending.forEach((item, itemIndex) => {
    const steps = splitPoints(item.notes);
    const titles = steps.length > 0 ? steps : [item.title];

    titles.forEach((title, stepIndex) => {
      const baseMinutes = steps.length > 1 ? 25 : 30;
      const minutes = shorter ? Math.max(15, Math.round(baseMinutes * 0.6)) : baseMinutes;
      const slot = slots[counter % slots.length];

      let date: string;
      if (saturday) date = saturday;
      else if (tomorrow) date = tomorrow;
      else if (item.dueDate && item.dueDate >= today) {
        // Spread the steps of this goal across the days up to its deadline.
        const span = Math.max(0, Math.min(3, titles.length - 1));
        const offset = span === 0 ? 0 : Math.round((stepIndex / span) * span);
        date = addDays(today, offset);
        if (date > item.dueDate) date = item.dueDate;
      } else {
        date = addDays(today, Math.min(2, itemIndex));
      }

      tasks.push({
        id: counter + 1,
        sourceId: item.id,
        title,
        dueDate: date,
        startTime: slot,
        endTime: addMinutes(slot, minutes),
        estimatedMinutes: minutes,
        priority: item.priority,
      });
      counter += 1;
    });
  });

  return tasks.map((task, index) => ({ ...task, id: index + 1 }));
}

export function draftTotalMinutes(tasks: DraftTask[]): number {
  return tasks.reduce((sum, task) => sum + task.estimatedMinutes, 0);
}

/** Send the confirmed draft back as goal description lines (api fallback). */
export function draftToDescription(tasks: DraftTask[]): string {
  return tasks
    .map((task) => `${task.title}｜${task.dueDate} ${task.startTime}（约 ${task.estimatedMinutes} 分钟）`)
    .join('\n');
}
