/** Shared, dependency-free validation for task edit forms. */

export const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

/** Blank → null, invalid → 'invalid', otherwise an integer in 1..600. */
export function parseEstimatedMinutes(value: string): number | null | 'invalid' {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^\d+$/.test(trimmed)) return 'invalid';
  const minutes = Number(trimmed);
  if (!Number.isInteger(minutes) || minutes < 1 || minutes > 600) return 'invalid';
  return minutes;
}

/** Trim a time input; blank becomes null so the backend clears the field. */
export function normalizeTime(value: string): string | null {
  const trimmed = value.trim();
  return trimmed || null;
}

export function isValidTime(value: string): boolean {
  const trimmed = value.trim();
  return trimmed === '' || TIME_PATTERN.test(trimmed);
}

/** `HH:MM` compares correctly as strings; one blank side is accepted. */
export function isEndAfterStart(start: string, end: string): boolean {
  const s = start.trim();
  const e = end.trim();
  if (!s || !e) return true;
  if (!TIME_PATTERN.test(s) || !TIME_PATTERN.test(e)) return true;
  return e > s;
}
