import type { TraitDomainKey, TraitSnapshot } from '@/api/types';

/** Presentation metadata for the Big Five. These are labels, not model maths. */
export const TRAIT_ORDER: TraitDomainKey[] = ['N', 'E', 'O', 'A', 'C'];

export const TRAIT_META: Record<
  TraitDomainKey,
  { name: string; short: string; description: string }
> = {
  N: {
    name: '情绪敏感性',
    short: 'N',
    description: '对压力、担忧和情绪波动的敏感程度。',
  },
  E: {
    name: '外向性',
    short: 'E',
    description: '从社交和外部活动中获得能量的倾向。',
  },
  O: {
    name: '开放性',
    short: 'O',
    description: '对新想法、审美和抽象概念的兴趣。',
  },
  A: {
    name: '宜人性',
    short: 'A',
    description: '在合作中体谅、信任他人的倾向。',
  },
  C: {
    name: '尽责性',
    short: 'C',
    description: '计划、坚持和按部就班完成任务的倾向。',
  },
};

function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}

/** Map theta to a 0..1 bar position; 0.5 is the population midpoint. */
export function traitPosition(theta: number): number {
  if (!Number.isFinite(theta)) return 0.5;
  return clamp((theta + 2.5) / 5, 0, 1);
}

/** User-facing band; deliberately not a percentile. */
export function traitBand(theta: number): '偏低' | '中等' | '偏高' {
  if (!Number.isFinite(theta)) return '中等';
  if (theta <= -0.5) return '偏低';
  if (theta >= 0.5) return '偏高';
  return '中等';
}

/** A qualitative uncertainty label; SE is never presented as accuracy. */
export function uncertaintyLabel(se: number): string {
  if (!Number.isFinite(se)) return '未知';
  if (se <= 0.3) return '较稳定';
  if (se <= 0.5) return '中等';
  return '较不确定';
}

/** Narrow a raw backend trait profile (e.g. assessment completion) safely. */
export function asTraitSnapshot(raw: unknown): TraitSnapshot | null {
  if (!raw || typeof raw !== 'object') return null;
  const candidate = raw as { domains?: unknown };
  if (!candidate.domains || typeof candidate.domains !== 'object') return null;
  const domains = candidate.domains as Record<string, { theta?: unknown }>;
  const valid = TRAIT_ORDER.every(
    (key) => domains[key] && typeof domains[key].theta === 'number',
  );
  return valid ? (raw as TraitSnapshot) : null;
}