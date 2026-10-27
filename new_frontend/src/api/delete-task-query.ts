export type DeleteTaskScope = 'single' | 'series';

export type DeleteTaskOptions = {
  scope?: DeleteTaskScope;
  reason?: string | null;
};

/**
 * Query string for `DELETE /plans/{planId}/tasks/{taskId}`. Kept pure so the
 * scope/reason encoding is testable without importing the fetch client.
 */
export function deleteTaskQuery(options: DeleteTaskOptions = {}): string {
  const params: string[] = [];
  if (options.scope) params.push(`scope=${encodeURIComponent(options.scope)}`);
  if (options.reason) params.push(`reason=${encodeURIComponent(options.reason)}`);
  return params.length > 0 ? `?${params.join('&')}` : '';
}
