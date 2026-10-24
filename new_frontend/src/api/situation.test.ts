import { describe, expect, it } from 'vitest';

import { situationFromTrends } from '@/api/mapper';
import type { SituationTrendRead } from '@/api/types';

describe('situation projection', () => {
  it('keeps missing feedback null instead of inventing a value', () => {
    const raw: SituationTrendRead = {
      points: [
        { date: '2026-10-22', energy: null, stress: null, efficacy: null },
        { date: '2026-10-23', energy: 6, stress: null, efficacy: null },
      ],
      samples: 2,
      min_samples: 5,
      sufficient: false,
      drivers: ['only two days'],
    };
    const situation = situationFromTrends(raw);
    expect(situation.energy).toBe(6);
    expect(situation.stress).toBeNull();
    expect(situation.efficacy).toBe(0);
    expect(situation.points[0].energy).toBeNull();
    expect(situation.sufficient).toBe(false);
    expect(situation.reasons).toEqual(['only two days']);
  });

  it('uses the last non-null efficacy', () => {
    const raw: SituationTrendRead = {
      points: [
        { date: '2026-10-22', energy: 5, stress: 4, efficacy: 0.4 },
        { date: '2026-10-23', energy: 5, stress: 4, efficacy: null },
      ],
      samples: 2,
      min_samples: 5,
      sufficient: false,
      drivers: [],
    };
    expect(situationFromTrends(raw).efficacy).toBe(0.4);
  });
});