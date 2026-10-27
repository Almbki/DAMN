/**
 * Browser-side caches that belong to the signed-in user. They are not server
 * data; they must be dropped on logout / 401 so the next account never sees a
 * previous user's preview, preferences or feedback marker.
 */

type RemovableStorage = {
  removeItem(key: string): void;
};

const GLOBAL_KEYS = ['damn.preferences', 'damn.feedback.lastDate'];

function previewKeys(userId: number): string[] {
  return [`damn.preview.v1.${userId}`, `damn.preview.dismissed.v1.${userId}`];
}

function resolveStorage(storage?: RemovableStorage | null): RemovableStorage | null {
  if (storage !== undefined) return storage;
  if (typeof globalThis.localStorage === 'undefined') return null;
  return globalThis.localStorage;
}

export function clearUserScopedCaches(
  userId: number | null,
  storage?: RemovableStorage | null,
): void {
  const target = resolveStorage(storage);
  if (!target) return;
  const keys = userId == null ? GLOBAL_KEYS : [...previewKeys(userId), ...GLOBAL_KEYS];
  for (const key of keys) {
    try {
      target.removeItem(key);
    } catch {
      // Storage can be unavailable (private mode/quota); cleanup is best-effort.
    }
  }
}
