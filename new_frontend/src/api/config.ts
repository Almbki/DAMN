/**
 * Runtime config. `EXPO_PUBLIC_*` values are inlined at build time, so changing
 * `.env` requires restarting the dev server with `--clear`.
 */

export type DataSource = 'mock' | 'api';

const source = process.env.EXPO_PUBLIC_DATA_SOURCE;

export const dataSource: DataSource = source === 'api' ? 'api' : 'mock';

/**
 * Resolve the backend origin.
 *
 * 1. `EXPO_PUBLIC_API_BASE_URL` wins when set (build-time inlined).
 * 2. Otherwise, on web, derive it from the page host + `EXPO_PUBLIC_API_PORT`
 *    (default 8000). This is what makes a **static web export** work when it is
 *    served by a plain file server (`python -m http.server`) instead of Metro:
 *    without this the app would POST to `<static-server>/api/v1/...` and get
 *    501/404 (the classic "连不上后端" symptom).
 */
function resolveApiBaseUrl(): string {
  const configured = (process.env.EXPO_PUBLIC_API_BASE_URL ?? '').replace(/\/+$/, '');
  if (configured) return configured;

  const location = (globalThis as { location?: { hostname?: string; protocol?: string } })
    .location;
  if (location?.hostname) {
    const protocol = location.protocol === 'https:' ? 'https:' : 'http:';
    const port = process.env.EXPO_PUBLIC_API_PORT ?? '8000';
    return `${protocol}//${location.hostname}:${port}`;
  }
  return '';
}

export const apiBaseUrl = resolveApiBaseUrl();

export const apiPrefix = '/api/v1';

export const devEmail = process.env.EXPO_PUBLIC_DEV_EMAIL ?? 'demo@damn.app';
export const devPassword = process.env.EXPO_PUBLIC_DEV_PASSWORD ?? 'password123';

/** The LAN backend has been measured stalling ~18s; keep this generous. */
export const requestTimeoutMs = 30_000;

/** Poll cadence for `apiPollJob` when the SSE stream is unavailable. */
export const pollIntervalMs = 1500;

/**
 * Wall-clock guard for a whole generation job. The SSE stream has no
 * per-request timeout (the stream stays open until the job ends), so the
 * caller bounds it here instead.
 */
export const streamTimeoutMs = 180_000;
