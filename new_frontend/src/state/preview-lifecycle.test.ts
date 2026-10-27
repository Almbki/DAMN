import { describe, expect, it } from 'vitest';

import { shouldRestorePreview } from '@/state/preview-lifecycle';

describe('shouldRestorePreview', () => {
  it('restores a preview whose thread has not been dismissed', () => {
    expect(shouldRestorePreview('thread-new', null)).toBe(true);
    expect(shouldRestorePreview('thread-new', 'thread-old')).toBe(true);
  });

  it('does not restore the thread that was dismissed/consumed', () => {
    expect(shouldRestorePreview('thread-1', 'thread-1')).toBe(false);
  });

  it('does not restore a missing thread id', () => {
    expect(shouldRestorePreview(null, null)).toBe(false);
    expect(shouldRestorePreview(undefined, null)).toBe(false);
    expect(shouldRestorePreview('', null)).toBe(false);
  });
});
