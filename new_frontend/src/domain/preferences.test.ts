import { describe, expect, it } from 'vitest';

import {
  DEFAULT_PREFERENCES,
  normalizePreferences,
  preferencesFromApi,
  preferencesToApi,
} from '@/domain/preferences';

describe('scheduling preferences', () => {
  it('defaults overdue auto-backlog to off', () => {
    expect(DEFAULT_PREFERENCES.autoBacklogOverdue).toBe(false);
    expect(normalizePreferences(DEFAULT_PREFERENCES).autoBacklogOverdue).toBe(false);
  });

  it('normalizes the toggle with Boolean', () => {
    expect(
      normalizePreferences({
        ...DEFAULT_PREFERENCES,
        autoBacklogOverdue: 1 as unknown as boolean,
      }).autoBacklogOverdue,
    ).toBe(true);
    expect(
      normalizePreferences({
        ...DEFAULT_PREFERENCES,
        autoBacklogOverdue: 0 as unknown as boolean,
      }).autoBacklogOverdue,
    ).toBe(false);
  });

  it('reads the snake_case field from the API and defaults it to false', () => {
    const base = {
      available_minutes_per_day: 420,
      daily_limit_minutes: 240,
      buffer_minutes: 10,
      high_cognitive_max_per_day: 1,
    };
    expect(preferencesFromApi({ ...base, auto_backlog_overdue: true }).autoBacklogOverdue).toBe(
      true,
    );
    expect(preferencesFromApi(base).autoBacklogOverdue).toBe(false);
  });

  it('writes the toggle back to the API payload', () => {
    const payload = preferencesToApi({
      ...DEFAULT_PREFERENCES,
      autoBacklogOverdue: true,
    });
    expect(payload.auto_backlog_overdue).toBe(true);
  });
});
