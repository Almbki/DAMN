/**
 * Runtime config. `EXPO_PUBLIC_*` values are inlined at build time, so changing
 * `.env` requires restarting the dev server with `--clear`.
 */

export type DataSource = 'mock' | 'api';

const source = process.env.EXPO_PUBLIC_DATA_SOURCE;

export const dataSource: DataSource = source === 'api' ? 'api' : 'mock';

export const apiBaseUrl = (process.env.EXPO_PUBLIC_API_BASE_URL ?? '').replace(/\/+$/, '');

export const apiPrefix = '/api/v1';

export const devEmail = process.env.EXPO_PUBLIC_DEV_EMAIL ?? 'demo@damn.app';
export const devPassword = process.env.EXPO_PUBLIC_DEV_PASSWORD ?? 'password123';

/** The LAN backend has been measured stalling ~18s; keep this generous. */
export const requestTimeoutMs = 30_000;
