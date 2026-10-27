/**
 * Pure maths for the timetable's long-press drag.
 *
 * The backend snaps a MOVE start to the nearest 30 minutes (half-up), so the
 * local preview must use exactly the same rule. The duration is not snapped:
 * a 75-minute task dropped at 09:30 still ends at 10:45.
 */

export const GRID_SLOT_MINUTES = 30;

export type TimeGrid = {
  days: readonly string[];
  dayWidth: number;
  hourHeight: number;
  /** First minute represented by the grid, e.g. 360 for 06:00. */
  dayStart: number;
  /** Exclusive end minute, e.g. 1440 for 24:00. */
  dayEnd: number;
  slotMinutes?: number;
};

export type DropTarget = { date: string; start: string };

/** `HH:MM` / `HH:MM:SS` → minutes after midnight; null when malformed. */
export function timeToMinutes(value: string | null | undefined): number | null {
  if (!value) return null;
  const match = /^(\d{1,2}):(\d{2})/.exec(value.trim());
  if (!match) return null;
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (!Number.isInteger(hours) || !Number.isInteger(minutes)) return null;
  if (hours > 24 || minutes > 59) return null;
  const total = hours * 60 + minutes;
  return total > 24 * 60 ? null : total;
}

/** Minutes after midnight → zero-padded `HH:MM` (24:00 stays 24:00). */
export function minutesToTime(minutes: number): string {
  const total = Math.max(0, Math.round(minutes));
  const hours = Math.floor(total / 60);
  const mins = total % 60;
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
}

/** Nearest grid line, half-up: 14:15 → 14:30, 14:14 → 14:00. */
export function snapMinutesToGrid(
  minutes: number,
  stepMinutes: number = GRID_SLOT_MINUTES,
): number {
  const step = Math.max(1, Math.round(stepMinutes));
  return Math.round(minutes / step) * step;
}

/** Add a duration without snapping the end. */
export function addMinutesToTime(start: string, minutes: number): string | null {
  const startMinutes = timeToMinutes(start);
  if (startMinutes == null || !Number.isFinite(minutes)) return null;
  return minutesToTime(startMinutes + minutes);
}

/**
 * Map a pointer inside the week body to a day + snapped start time.
 * `position` is relative to the body's top-left (the seven-day canvas).
 */
export function dropTargetFromPosition(
  position: { x: number; y: number },
  grid: TimeGrid,
): DropTarget | null {
  const { days, dayWidth, hourHeight, dayStart, dayEnd } = grid;
  const slot = grid.slotMinutes ?? GRID_SLOT_MINUTES;
  if (days.length === 0 || dayWidth <= 0 || hourHeight <= 0 || dayEnd <= dayStart) {
    return null;
  }

  const width = dayWidth * days.length;
  const height = ((dayEnd - dayStart) / 60) * hourHeight;
  if (position.x < 0 || position.x >= width) return null;
  if (position.y < 0 || position.y >= height) return null;

  const dayIndex = Math.min(days.length - 1, Math.floor(position.x / dayWidth));
  const rawMinutes = dayStart + (position.y / hourHeight) * 60;
  const lastStart = dayEnd - slot;
  const snapped = Math.min(
    lastStart,
    Math.max(dayStart, snapMinutesToGrid(rawMinutes, slot)),
  );

  return { date: days[dayIndex], start: minutesToTime(snapped) };
}
