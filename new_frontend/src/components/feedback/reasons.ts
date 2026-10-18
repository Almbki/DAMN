/**
 * The per-task reason vocabulary shared by the feedback form and history.
 *
 * The backend stores reasons as free strings, so new keys can appear in older
 * feedback rows. `taskReasonLabel` falls back to the raw string instead of
 * hiding unknown values.
 */

export type TaskReasonKey =
  | 'interrupted'
  | 'not_enough_time'
  | 'too_hard'
  | 'low_energy'
  | 'didnt_want'
  | 'skipped'
  | 'other';

export const TASK_REASON_LABEL: Record<TaskReasonKey, string> = {
  interrupted: '被打断',
  not_enough_time: '时间不够',
  too_hard: '太难',
  low_energy: '精力不足',
  didnt_want: '不想做',
  skipped: '今天先不做',
  other: '其他',
};

export const TASK_REASON_OPTIONS: { key: TaskReasonKey; label: string }[] = [
  { key: 'interrupted', label: TASK_REASON_LABEL.interrupted },
  { key: 'not_enough_time', label: TASK_REASON_LABEL.not_enough_time },
  { key: 'too_hard', label: TASK_REASON_LABEL.too_hard },
  { key: 'low_energy', label: TASK_REASON_LABEL.low_energy },
  { key: 'didnt_want', label: TASK_REASON_LABEL.didnt_want },
  { key: 'skipped', label: TASK_REASON_LABEL.skipped },
  { key: 'other', label: TASK_REASON_LABEL.other },
];

export function taskReasonLabel(value: string | null | undefined): string {
  if (!value) return '';
  return TASK_REASON_LABEL[value as TaskReasonKey] ?? value;
}
