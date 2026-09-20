/**
 * 日期 / 时长的小工具。
 *
 * ## 为什么必须有这个文件
 *
 * 后端的时间字段是裸的 wire 格式，直接丢给 `Date` 会踩两个坑：
 *
 * 1. `"08:00:00"`（`format: time`）**不是合法日期字符串**，`new Date()` 得到
 *    `Invalid Date` —— 必须自己拆时/分。
 * 2. `"2026-09-19"`（`format: date`）被 JS 当作 **UTC 午夜**解析，在东八区
 *    会变成前一天 08:00。所以「今天是哪天」必须用**本地时间**拼，不能用
 *    `toISOString().slice(0, 10)`。
 */

function pad2(value: number): string {
  return value < 10 ? `0${value}` : String(value);
}

/** 本地时区的 `"YYYY-MM-DD"`。**不要**用 `toISOString()` 代替。 */
export function toLocalDateString(date: Date = new Date()): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

/** 今天（本地）的 `"YYYY-MM-DD"`。 */
export function todayString(): string {
  return toLocalDateString();
}

/** `"2026-09-19"` → 本地 `Date`（当天的本地午夜，不是 UTC）。 */
export function parseDateString(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

/** `"08:00:00"` / `"08:00"` → 当天零点起的分钟数。解析不了返回 `null`。 */
export function parseTimeToMinutes(value: string | null | undefined): number | null {
  if (!value) return null;
  const match = /^(\d{1,2}):(\d{2})/.exec(value);
  if (!match) return null;
  return Number(match[1]) * 60 + Number(match[2]);
}

/** `"08:00:00"` → `"08:00"`（界面上不显示秒）。 */
export function formatClock(value: string | null | undefined): string | null {
  const minutes = parseTimeToMinutes(value);
  if (minutes === null) return null;
  return `${pad2(Math.floor(minutes / 60))}:${pad2(minutes % 60)}`;
}

/** 当前本地时间的 `"HH:MM"`。 */
export function nowClock(date: Date = new Date()): string {
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

/** `"2026-09-19"` → `"9月19日"`。 */
export function formatMonthDay(value: string | null | undefined): string {
  const parsed = value ? parseDateString(value) : null;
  if (!parsed) return '';
  return `${parsed.getMonth() + 1}月${parsed.getDate()}日`;
}

/** 分钟数 → `"2 小时 18 分钟"` / `"25 分钟"`。 */
export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} 小时` : `${hours} 小时 ${rest} 分钟`;
}

/** 计划还剩几天（含今天）。 */
export function daysBetween(startDate: string, endDate: string): number | null {
  const start = parseDateString(startDate);
  const end = parseDateString(endDate);
  if (!start || !end) return null;
  return Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1;
}

/**
 * 完整的 ISO 时间（`"2026-09-19T18:13:29.232147+08:00"`）→ `"9月19日 18:13"`。
 *
 * 这种带时区的字符串 `new Date()` 能正确解析，所以直接用；只有裸的
 * `"YYYY-MM-DD"` 和 `"HH:MM:SS"` 才需要手动处理（见文件顶部）。
 * 解析失败时原样返回，不假装知道答案。
 */
export function formatDateTimeLabel(iso: string | null | undefined): string {
  if (!iso) return '';
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return `${parsed.getMonth() + 1}月${parsed.getDate()}日 ${pad2(parsed.getHours())}:${pad2(
    parsed.getMinutes(),
  )}`;
}
