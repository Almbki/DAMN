/**
 * MBTI metadata for the 基础画像 picker. Pure — no React, no network.
 *
 * `MBTI_TYPES` follows the backend's valid set in its conventional grouping;
 * the weight rule matches `app/domain/profile/engine.py`: each dimension weight
 * is the pull toward the FIRST letter (I / S / T / J), and the letter at
 * `>= 0.5` is the majority one.
 */

export const MBTI_TYPES = [
  'ISTJ',
  'ISFJ',
  'INFJ',
  'INTJ',
  'ISTP',
  'ISFP',
  'INFP',
  'INTP',
  'ESTP',
  'ESFP',
  'ENFP',
  'ENTP',
  'ESTJ',
  'ESFJ',
  'ENFJ',
  'ENTJ',
] as const;

export type MbtiType = (typeof MBTI_TYPES)[number];

export const MBTI_DIMENSIONS = ['ie', 'sn', 'tf', 'jp'] as const;
export type MbtiDimension = (typeof MBTI_DIMENSIONS)[number];

/** First letter wins when the weight is `>= 0.5` (mirrors the backend). */
export const DIMENSION_LETTERS: Record<MbtiDimension, readonly [string, string]> = {
  ie: ['I', 'E'],
  sn: ['S', 'N'],
  tf: ['T', 'F'],
  jp: ['J', 'P'],
};

/** The 16-type grid is always four columns wide. */
export const GRID_COLUMNS = 4;

/** Dimension weights are `0..1`; backends and sliders both clamp. */
export type MbtiWeights = Record<MbtiDimension, number>;

const MBTI_SET: ReadonlySet<string> = new Set<string>(MBTI_TYPES);

export function isMbtiType(value: string): value is MbtiType {
  return MBTI_SET.has(value.toUpperCase());
}

/** Case-insensitive / whitespace-tolerant parse; `null` when not a valid type. */
export function normalizeMbti(value: string | null | undefined): MbtiType | null {
  if (!value) return null;
  const upper = value.trim().toUpperCase();
  return isMbtiType(upper) ? upper : null;
}

export function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

/** The pure weights implied by a type: 1 for its own letters, 0 for the others. */
export function dimsForType(type: MbtiType): MbtiWeights {
  const dims = {} as MbtiWeights;
  MBTI_DIMENSIONS.forEach((dim, index) => {
    dims[dim] = type[index] === DIMENSION_LETTERS[dim][0] ? 1 : 0;
  });
  return dims;
}

/** Flip the letter at `dimension` to the majority letter of `weight`. */
export function typeWithDimension(
  type: MbtiType,
  dimension: MbtiDimension,
  weight: number,
): MbtiType {
  const index = MBTI_DIMENSIONS.indexOf(dimension);
  const majority = DIMENSION_LETTERS[dimension][weight >= 0.5 ? 0 : 1];
  const next = type.slice(0, index) + majority + type.slice(index + 1);
  return isMbtiType(next) ? next : type;
}

/**
 * Fill a possibly-partial `mbti_dims` payload into all four axes, using the
 * type's own letters as the base so an omitted axis never silently flips it.
 */
export function dimsFromPayload(
  type: MbtiType | null,
  payload: Partial<MbtiWeights> | null | undefined,
): MbtiWeights | null {
  const provided = payload ?? {};
  const keys = MBTI_DIMENSIONS.filter((dim) => typeof provided[dim] === 'number');
  if (keys.length === 0) return type ? dimsForType(type) : null;
  const base: MbtiWeights = type ? dimsForType(type) : { ie: 0.5, sn: 0.5, tf: 0.5, jp: 0.5 };
  MBTI_DIMENSIONS.forEach((dim) => {
    const value = provided[dim];
    if (typeof value === 'number') base[dim] = clamp01(value);
  });
  return base;
}

/** Re-resolve the type after dims changed, so the grid cell follows the sliders. */
export function resolveType(type: MbtiType | null, dims: MbtiWeights | null): MbtiType | null {
  if (!type || !dims) return type;
  return MBTI_DIMENSIONS.reduce(
    (current, dim) => typeWithDimension(current, dim, dims[dim]),
    type,
  );
}

/**
 * Return `dims` only when they are a genuine refinement of the type; a set that
 * merely restates the type's own letters (all 0/1) collapses to `null`. Keeps
 * the "unsaved changes" check stable when the backend echoes pure dims back.
 */
export function explicitDims(type: MbtiType | null, dims: MbtiWeights | null): MbtiWeights | null {
  if (!type || !dims) return null;
  const pure = dimsForType(type);
  const isPure = MBTI_DIMENSIONS.every((dim) => Math.abs(dims[dim] - pure[dim]) < 1e-6);
  return isPure ? null : dims;
}

/** Split a flat list into fixed-width rows (no `flexWrap` on react-native-web). */
export function chunk<T>(items: readonly T[], size: number): T[][] {
  const rows: T[][] = [];
  for (let index = 0; index < items.length; index += size) {
    rows.push(items.slice(index, index + size));
  }
  return rows;
}
