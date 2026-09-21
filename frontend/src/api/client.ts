import { apiBaseUrl, apiPrefix, requestTimeoutMs } from '@/api/config';

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
