import { describe, expect, it } from 'vitest';

import { clearUserScopedCaches } from '@/state/user-cache';

function mockStorage(initialKeys: string[]) {
  const keys = new Set(initialKeys);
  const removed: string[] = [];
  return {
    keys,
    removed,
    removeItem(key: string) {
      removed.push(key);
      keys.delete(key);
    },
  };
}

describe('clearUserScopedCaches', () => {
  it('removes exactly the user preview keys plus the global caches', () => {
    const storage = mockStorage([
      'damn.preview.v1.7',
      'damn.preview.dismissed.v1.7',
      'damn.preferences',
      'damn.feedback.lastDate',
      'damn.authToken',
      'damn.preview.v1.8',
      'damn.preview.dismissed.v1.8',
    ]);

    clearUserScopedCaches(7, storage);

    expect(storage.removed.sort()).toEqual(
      [
        'damn.preview.dismissed.v1.7',
        'damn.preview.v1.7',
        'damn.feedback.lastDate',
        'damn.preferences',
      ].sort(),
    );
    expect(storage.keys.has('damn.authToken')).toBe(true);
    expect(storage.keys.has('damn.preview.v1.8')).toBe(true);
    expect(storage.keys.has('damn.preview.dismissed.v1.8')).toBe(true);
  });

  it('still clears the global caches when the user id is unknown', () => {
    const storage = mockStorage([
      'damn.preferences',
      'damn.feedback.lastDate',
      'damn.preview.v1.7',
      'damn.preview.dismissed.v1.7',
      'damn.authToken',
    ]);

    clearUserScopedCaches(null, storage);

    expect(storage.removed.sort()).toEqual(
      ['damn.feedback.lastDate', 'damn.preferences'].sort(),
    );
    expect(storage.keys.has('damn.preview.v1.7')).toBe(true);
    expect(storage.keys.has('damn.preview.dismissed.v1.7')).toBe(true);
    expect(storage.keys.has('damn.authToken')).toBe(true);
  });

  it('is a no-op without storage and survives storage errors', () => {
    expect(() => clearUserScopedCaches(7, null)).not.toThrow();

    const throwing = {
      removeItem() {
        throw new Error('quota');
      },
    };
    expect(() => clearUserScopedCaches(7, throwing)).not.toThrow();
  });
});
