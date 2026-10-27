/** The single copy shown whenever an active-plan edit is blocked by a preview. */
export const PLAN_LOCK_MESSAGE = '请先完成当前计划';

export type PlanLockState = {
  /** A generation/adjust/confirm request is in flight. */
  previewBusy: boolean;
  /** A generated but unconfirmed preview exists. */
  hasPreview: boolean;
};

/**
 * Editing is locked while a preview is being generated or while a generated
 * preview is waiting for confirmation. Viewing and navigation stay available.
 */
export function isPlanEditingLocked(state: PlanLockState): boolean {
  return state.previewBusy || state.hasPreview;
}
