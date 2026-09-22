// `expo/fetch` is the runtime's global fetch and the guaranteed-streaming form.
// Aliased so the existing `apiRequest` keeps using the global `fetch` untouched.
import { fetch as expoFetch } from 'expo/fetch';

import { apiBaseUrl, apiPrefix, pollIntervalMs, requestTimeoutMs, streamTimeoutMs } from '@/api/config';
import type { JobStatus } from '@/api/types';

export class ApiError extends Error {
  status: number;
  code: string;
  detail: unknown;

  constructor(status: number, code: string, message: string, detail: unknown = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  auth?: boolean;
  timeoutMs?: number;
};

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/**
 * Fetch wrapper: prefixes `/api/v1`, attaches the bearer token, enforces a
 * timeout, and normalises the backend error envelope `{code, message, detail}`.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true, timeoutMs = requestTimeoutMs } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (auth && authToken) headers.Authorization = `Bearer ${authToken}`;

    const response = await fetch(`${apiBaseUrl}${apiPrefix}${path}`, {
      method,
      headers,
      signal: controller.signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    const text = await response.text();
    const data = text ? parseJson(text) : null;

    if (!response.ok) {
      const envelope = (data ?? {}) as { code?: string; message?: string; detail?: unknown };
      throw new ApiError(
        response.status,
        envelope.code ?? 'http_error',
        envelope.message ?? `请求失败（HTTP ${response.status}）`,
        envelope.detail ?? null,
      );
    }

    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError(0, 'timeout', '请求超时，后端没有响应。');
    }
    throw new ApiError(0, 'network_error', '连不上后端，检查网络或后端地址。');
  } finally {
    clearTimeout(timer);
  }
}

type StreamHandlers = {
  onStage: (stage: string, data: any) => void;
};

type ExpoResponse = Awaited<ReturnType<typeof expoFetch>>;

function abortError(): ApiError {
  return new ApiError(0, 'aborted', '请求已取消。');
}

/** Split one raw SSE frame into `event:` / `data:` parts and dispatch it. */
function dispatchFrame(frame: string, onStage: (stage: string, data: any) => void): void {
  let stage = '';
  const dataLines: string[] = [];

  for (const line of frame.split('\n')) {
    if (line.startsWith(':')) continue; // heartbeat / comment
    if (line.startsWith('event:')) {
      stage = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).replace(/^ /, ''));
    }
  }

  if (!stage && dataLines.length === 0) return;

  const raw = dataLines.join('\n');
  let data: unknown = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = raw;
    }
  }
  onStage(stage || 'message', data);
}

/**
 * Consume an SSE endpoint. Each frame is `event: <stage>` plus a JSON `data:`
 * line; `:comment` heartbeat lines are ignored. Throws `ApiError(0,'no_stream')`
 * when `response.body` is unavailable so the caller can fall back to polling.
 */
export async function apiStream(
  path: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const headers: Record<string, string> = { Accept: 'text/event-stream' };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  let response: ExpoResponse;
  try {
    response = await expoFetch(`${apiBaseUrl}${apiPrefix}${path}`, {
      method: 'GET',
      headers,
      signal,
    });
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (signal?.aborted || (error instanceof Error && error.name === 'AbortError')) {
      throw abortError();
    }
    throw new ApiError(0, 'network_error', '连不上后端，检查网络或后端地址。');
  }

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    const data = text ? parseJson(text) : null;
    const envelope = (data ?? {}) as { code?: string; message?: string; detail?: unknown };
    throw new ApiError(
      response.status,
      envelope.code ?? 'http_error',
      envelope.message ?? `请求失败（HTTP ${response.status}）`,
      envelope.detail ?? null,
    );
  }

  if (!response.body) {
    throw new ApiError(0, 'no_stream', '当前平台不支持流式响应，已改用轮询。');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, '\n');
      let boundary = buffer.indexOf('\n\n');
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        dispatchFrame(frame, handlers.onStage);
        boundary = buffer.indexOf('\n\n');
      }
    }
    buffer += decoder.decode();
    buffer = buffer.replace(/\r\n/g, '\n');
    const tail = buffer.trim();
    if (tail) dispatchFrame(tail, handlers.onStage);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (signal?.aborted || (error instanceof Error && error.name === 'AbortError')) {
      throw abortError();
    }
    throw new ApiError(0, 'stream_error', '生成流中断，已改用轮询。');
  } finally {
    reader.cancel().catch(() => undefined);
  }
}

function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(abortError());
      return;
    }
    let timer: ReturnType<typeof setTimeout> | undefined;
    const onAbort = () => {
      if (timer !== undefined) clearTimeout(timer);
      reject(abortError());
    };
    timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

/**
 * Poll `GET /plans/generation/{job_id}` every `intervalMs` until the job is
 * `completed`/`failed`, or throw `ApiError(0,'timeout')` past `timeoutMs`.
 */
export async function apiPollJob(
  statusPath: string,
  opts: { intervalMs?: number; timeoutMs?: number; signal?: AbortSignal } = {},
): Promise<JobStatus> {
  const { intervalMs = pollIntervalMs, timeoutMs = streamTimeoutMs, signal } = opts;
  const startedAt = Date.now();

  for (;;) {
    if (signal?.aborted) throw abortError();
    const status = await apiRequest<JobStatus>(statusPath);
    if (status.status === 'completed' || status.status === 'failed') return status;
    if (Date.now() - startedAt >= timeoutMs) {
      throw new ApiError(0, 'timeout', '生成超时，请稍后重试。');
    }
    await delay(intervalMs, signal);
  }
}
