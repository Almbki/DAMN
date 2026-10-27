/**
 * A preview may only be rehydrated when it belongs to a real thread and that
 * thread was not already consumed/dismissed.
 */
export function shouldRestorePreview(
  threadId: string | null | undefined,
  dismissedThreadId: string | null,
): boolean {
  return Boolean(threadId) && threadId !== dismissedThreadId;
}
