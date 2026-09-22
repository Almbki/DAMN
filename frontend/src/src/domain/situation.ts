import type { FeedbackSample } from '@/domain/insight';

export type LoadLevel = 'low' | 'medium' | 'high';

export interface SituationPoint {
  date: string;
  /** 0..10, null when that day had no feedback for the metric. */
  energy: number | null;
  stress: number | null;
  /** 0..1 */
  efficacy: number | null;
}

export interface Situation {
  energy: number | null;
  stress: number | null;
  /** 0..1 composite; see `buildSituation` for the formula. */
  efficacy: number;
  points: SituationPoint[];
  samples: number;
  minSamples: number;
  sufficient: boolean;
  /** Plain-language "why the system says this". */
  reasons: string[];
}

const MIN_SAMPLES = 5;

function mean(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function round(value: number, digits = 1): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

/**
 * The backend has no "situation" endpoint or efficacy field yet, so this derives
 * one locally from what we do have: self-reported energy/stress per day plus the
 * execution weight and recent completion rate.
 *
 *   efficacy = 0.6 * execution_weight + 0.4 * recent_completion_rate
 *
 * The formula is surfaced in `reasons` so the number is never a black box.
 */
export function buildSituation(
  feedback: FeedbackSample[],
  executionWeight: number,
  completionRate: number,
  days = 14,
): Situation {
  const sorted = [...feedback]
    .filter((sample) => sample.energy_level != null || sample.stress_level != null)
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-days);

  const points: SituationPoint[] = sorted.map((sample) => {
    const dayCompletion = sample.completion_rate;
    const efficacy =
      dayCompletion != null
        ? clamp01(0.6 * executionWeight + 0.4 * dayCompletion)
        : clamp01(0.6 * executionWeight + 0.4 * completionRate);
    return {
      date: sample.date,
      energy: sample.energy_level,
      stress: sample.stress_level,
      efficacy,
    };
  });

  const latest = points.slice(-3);
  const energy = mean(latest.map((point) => point.energy).filter((v): v is number => v != null));
  const stress = mean(latest.map((point) => point.stress).filter((v): v is number => v != null));
  const efficacy = clamp01(0.6 * executionWeight + 0.4 * completionRate);

  const samples = points.length;
  const sufficient = samples >= MIN_SAMPLES;

  return {
    energy: energy == null ? null : round(energy),
    stress: stress == null ? null : round(stress),
    efficacy: round(efficacy, 2),
    points,
    samples,
    minSamples: MIN_SAMPLES,
    sufficient,
    reasons: buildReasons(energy, stress, executionWeight, completionRate, samples),
  };
}

function buildReasons(
  energy: number | null,
  stress: number | null,
  executionWeight: number,
  completionRate: number,
  samples: number,
): string[] {
  const reasons: string[] = [];

  if (energy != null) {
    reasons.push(
      energy >= 6.5
        ? `近几次反馈的精力均值 ${round(energy)}/10，偏高，系统按状态好多排一点。`
        : energy <= 3.5
          ? `近几次反馈的精力均值 ${round(energy)}/10，偏低，系统减少了单日任务量。`
          : `近几次反馈的精力均值 ${round(energy)}/10，中等，系统维持常规安排。`,
    );
  }

  if (stress != null) {
    if (stress >= 7) reasons.push(`压力均值 ${round(stress)}/10 偏高，高认知任务上限被压低。`);
    else if (stress <= 3)
      reasons.push(`压力均值 ${round(stress)}/10，平稳，可以承接稍难的任务。`);
  }

  reasons.push(
    `效能 = 执行权重 ${executionWeight.toFixed(2)} × 0.6 + 近期完成率 ${Math.round(
      completionRate * 100,
    )}% × 0.4。`,
  );

  if (samples < MIN_SAMPLES) {
    reasons.push(`目前只有 ${samples} 天反馈，样本不足 ${MIN_SAMPLES} 天，判断会随记录修正。`);
  }

  return reasons;
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}
