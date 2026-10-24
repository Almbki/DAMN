import { describe, expect, it } from 'vitest';

import {
  asTraitSnapshot,
  traitBand,
  traitPosition,
  uncertaintyLabel,
} from '@/domain/traits';

const valid = {
  model_version: 'trait_v1',
  schema_version: '1.0',
  calibration: {},
  metadata: {
    level: 'level1',
    model_version: 'trait_v1',
    artifact_version: 'grm_v1',
    artifact_hash: 'abc',
    feature_version: 'ipip_neo_grm_v1',
    mode: null,
    status: 'ok',
    degraded_reason: null,
  },
  domains: {
    N: { theta: 0, se: 0.3, ci95: [-0.5, 0.5], items_answered: 8 },
    E: { theta: 0, se: 0.3, ci95: [-0.5, 0.5], items_answered: 8 },
    O: { theta: 0, se: 0.3, ci95: [-0.5, 0.5], items_answered: 8 },
    A: { theta: 0, se: 0.3, ci95: [-0.5, 0.5], items_answered: 8 },
    C: { theta: 0, se: 0.3, ci95: [-0.5, 0.5], items_answered: 8 },
  },
};

describe('trait presentation', () => {
  it('uses bands, not percentiles', () => {
    expect(traitBand(-1)).toBe('偏低');
    expect(traitBand(0)).toBe('中等');
    expect(traitBand(1)).toBe('偏高');
  });

  it('maps theta onto a bounded bar with 0.5 as the midpoint', () => {
    expect(traitPosition(0)).toBeCloseTo(0.5);
    expect(traitPosition(-99)).toBe(0);
    expect(traitPosition(99)).toBe(1);
  });

  it('describes uncertainty qualitatively', () => {
    expect(uncertaintyLabel(0.2)).toBe('较稳定');
    expect(uncertaintyLabel(0.7)).toBe('较不确定');
  });

  it('accepts a complete profile and rejects malformed ones', () => {
    expect(asTraitSnapshot(valid)?.domains.N.theta).toBe(0);
    expect(asTraitSnapshot(null)).toBeNull();
    expect(asTraitSnapshot({ domains: { N: { theta: 0 } } })).toBeNull();
  });
});