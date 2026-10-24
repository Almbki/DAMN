/**
 * Runtime config. `EXPO_PUBLIC_*` values are inlined at build time, so changing
 * `.env` requires restarting the dev server with `--clear`.
 */

import Constants from 'expo-constants';
import { Platform } from 'react-native';

export type DataSource = 'mock' | 'api';

const source = process.env.EXPO_PUBLIC_DATA_SOURCE;

/** The backend is the default; mock mode is opt-in via an explicit value. */
export const dataSource: DataSource = source === 'mock' ? 'mock' : 'api';

const DEFAULT_API_PORT = '8000';

/** `host:port` / `exp://host:port` → `host`, tolerating a trailing path. */
function hostFromUri(uri: string | null | undefined): string | null {
  if (!uri) return null;
  const withoutScheme = uri.replace(/^[a-z]+:\/\//i, '');
  const host = withoutScheme.split('/')[0]?.split(':')[0]?.trim();
  return host || null;
}

/**
 * Resolve the backend origin.
 *
 * 1. `EXPO_PUBLIC_API_BASE_URL` wins when set (build-time inlined).
 * 2. Web: derive it from the page host + `EXPO_PUBLIC_API_PORT` (default 8000).
 *    This is what makes a static/single-page export work when it is served by a
 *    plain file server instead of Metro.
 * 3. Native: use the Metro host (`Constants.expoConfig.hostUri`) so a device on
 *    the LAN reaches the same machine that serves the JS bundle.
 * 4. Fallbacks: Android emulator `10.0.2.2`, iOS `localhost`.
 */
function resolveApiBaseUrl(): string {
  const configured = (process.env.EXPO_PUBLIC_API_BASE_URL ?? '').replace(/\/+$/, '');
  if (configured) return configured;

  const port = process.env.EXPO_PUBLIC_API_PORT ?? DEFAULT_API_PORT;

  if (Platform.OS === 'web') {
    const location = (globalThis as { location?: { hostname?: string; protocol?: string } })
      .location;
    if (location?.hostname) {
      const protocol = location.protocol === 'https:' ? 'https:' : 'http:';
      return `${protocol}//${location.hostname}:${port}`;
    }
    return `http://localhost:${port}`;
  }

  const metroHost = hostFromUri(Constants.expoConfig?.hostUri);
  if (metroHost) return `http://${metroHost}:${port}`;

  if (Platform.OS === 'android') return `http://10.0.2.2:${port}`;
  return `http://localhost:${port}`;
}

export const apiBaseUrl = resolveApiBaseUrl();

export const apiPrefix = '/api/v1';

export const demoEmail = (process.env.EXPO_PUBLIC_DEMO_EMAIL ?? '').trim();
export const demoPassword = process.env.EXPO_PUBLIC_DEMO_PASSWORD ?? '';
/** Auto demo login is enabled only when BOTH credentials are configured. */
export const demoLoginEnabled = Boolean(demoEmail && demoPassword);

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

/**
 * Inactivity guard for the SSE stream itself. A healthy backend sends a
 * heartbeat/frame well within this window; if it does not, the connection is
 * considered dead and the caller can fall back to polling.
 */
export const streamIdleTimeoutMs = 45_000;
