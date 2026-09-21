import type { DailyCompletionRead, InsightRead } from '@/api/types';
import type { Task } from '@/domain/task';

/** Mirrors the fields `insight_service.py` reads from feedback. */
export interface FeedbackSample {
  date: string;
  stress_level: number | null;
  energy_level: number | null;
  completion_rate?: number | null;
}

function round(value: number, digits: number): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function mean(values: number[]): number {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

/**
 * Local equivalent of `InsightService.get_insights`. Same shape as the backend
 * `InsightRead` so swapping to `GET /plans/{plan_id}/insights` changes nothing in
 * the panel.
 */
export function buildInsight(
  planId: number,
  tasks: Task[],
  feedback: FeedbackSample[],
): InsightRead {
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter((task) => task.done).length;
  const completionRate = totalTasks ? round(completedTasks / totalTasks, 3) : 0;

  const totalPlannedMinutes = tasks.reduce((sum, task) => sum + (task.estimatedMinutes ?? 0), 0);
  const totalActualMinutes = tasks.reduce((sum, task) => sum + (task.actualMinutes ?? 0), 0);

  const breakdown: Record<string, number> = { low: 0, medium: 0, high: 0 };
  let highCognitiveMinutes = 0;
  const dailyMap = new Map<string, DailyCompletionRead>();

  for (const task of tasks) {
    breakdown[task.cognitiveLoad] = (breakdown[task.cognitiveLoad] ?? 0) + 1;
    if (task.cognitiveLoad === 'high') highCognitiveMinutes += task.estimatedMinutes ?? 0;
    if (task.dueDate) {
      const entry =
        dailyMap.get(task.dueDate) ??
        ({ date: task.dueDate, total_tasks: 0, completed_tasks: 0, completion_rate: 0, planned_minutes: 0 } satisfies DailyCompletionRead);
      entry.total_tasks += 1;
      entry.planned_minutes += task.estimatedMinutes ?? 0;
      if (task.done) entry.completed_tasks += 1;
      dailyMap.set(task.dueDate, entry);
    }
  }

  const daily = Array.from(dailyMap.values())
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((entry) => ({
      ...entry,
      completion_rate: entry.total_tasks ? round(entry.completed_tasks / entry.total_tasks, 3) : 0,
    }));

  const stressValues = feedback
    .map((item) => item.stress_level)
    .filter((value): value is number => value != null);
  const energyValues = feedback
    .map((item) => item.energy_level)
    .filter((value): value is number => value != null);

  const executed = tasks.filter(
    (task) => task.done && task.actualMinutes != null && (task.estimatedMinutes ?? 0) > 0,
  );
  const plannedSum = executed.reduce((sum, task) => sum + (task.estimatedMinutes ?? 0), 0);
  const actualSum = executed.reduce((sum, task) => sum + (task.actualMinutes ?? 0), 0);
  const ratio = plannedSum ? round(actualSum / plannedSum, 3) : null;

  const avgStress = stressValues.length ? round(mean(stressValues), 2) : null;
  const avgEnergy = energyValues.length ? round(mean(energyValues), 2) : null;

  return {
    plan_id: planId,
    total_tasks: totalTasks,
    completed_tasks: completedTasks,
    completion_rate: completionRate,
    total_planned_minutes: totalPlannedMinutes,
    total_actual_minutes: totalActualMinutes,
    avg_stress: avgStress,
    avg_energy: avgEnergy,
    high_cognitive_minutes: highCognitiveMinutes,
    predicted_vs_actual_ratio: ratio,
    cognitive_load_breakdown: breakdown,
    daily,
    recommendations: recommend(ratio, completionRate, avgStress),
  };
}

/** Same rules as `InsightService._recommendations`, phrased for the UI. */
function recommend(
  ratio: number | null,
  completionRate: number,
  avgStress: number | null,
): string[] {
  const notes: string[] = [];
  if (ratio != null && ratio > 1.3) notes.push('实际用时明显高于预估，应该调高时长系数。');
  if (ratio != null && ratio < 0.7) notes.push('任务比预估更快完成，可以调低时长系数。');
  if (completionRate < 0.5) notes.push('完成率偏低，建议减少每日任务量或重新排。');
  if (avgStress != null && avgStress >= 7) notes.push('压力偏高，建议减少每天的高认知任务。');
  return notes;
}
