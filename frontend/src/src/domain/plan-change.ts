/**
 * "The system changed your next few days" — the shape the change notice reads.
 * The backend only has `ReplanEvent.changed_tasks` (ids, no dates) and no read
 * endpoint yet; see docs/design/backend-api-gaps.md §1.
 */
export interface PlanChangeDay {
  date: string;
  added: number;
  moved: number;
  removed: number;
  summary: string;
}

export interface PlanChange {
  id: number;
  triggerType: string;
  reason: string;
  oldVersion: number;
  newVersion: number;
  createdAt: string;
  days: PlanChangeDay[];
}
