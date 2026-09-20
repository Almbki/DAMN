/**
 * HTTP 客户端：一个 `fetch` 封装 + 一个错误类型。
 *
 * ## 为什么不用 axios
 *
 * 需要的东西只有三样：JSON 编解码、Bearer 头、把后端的错误信封变成异常。
 * 这些 `fetch` 都有，多一个依赖不划算（RN 里 axios 还得再配 adapter）。
 *
 * ## 两个后端的错误形状都要认
 *
 * 后端自己的错误是统一信封 `{code, message, detail}`，但 **Pydantic 校验失败
 * （422）走的是 FastAPI 默认结构** `{detail: [{loc, msg, type}]}`。只处理前者
 * 的话，所有校验错误都会变成一句无用的 "HTTP 422"。
 *
 * ## token 是显式传的
 *
 * 这里**不做**模块级全局 token 缓存。调用方（会话层/计划层）从 `useSession()`
 * 里拿 token 显式传进来 —— 避免出现"登出后某个闭包还攥着旧 token"这种问题。
 */

import { API_BASE_URL, API_PREFIX, REQUEST_TIMEOUT_MS } from './config';
import { formatDateTimeLabel } from './format';
import type { ErrorResponse } from './types';

/** 后端返回的错误。`status === 0` 表示压根没连上。 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail: unknown;

  constructor(status: number, code: string, message: string, detail: unknown = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
    // 目标环境是 esnext，但保底修一下原型链，避免 instanceof 在某些转译下失效
    Object.setPrototypeOf(this, ApiError.prototype);
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** 网络层失败（DNS / 拒绝连接 / 超时），不是后端返回的业务错误。 */
  get isOffline(): boolean {
    return this.status === 0;
  }
}

export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

export type RequestOptions = {
  method?: HttpMethod;
  body?: unknown;
  token?: string | null;
  /** 走根路径（只有 `/health` 是这样），不加 `/api/v1` 前缀 */
  root?: boolean;
  timeoutMs?: number;
  signal?: AbortSignal;
};

/** 拼出完整 URL。`root: true` 用于 `/health`。 */
export function apiUrl(path: string, root = false): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return root ? `${API_BASE_URL}${normalized}` : `${API_BASE_URL}${API_PREFIX}${normalized}`;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    method = 'GET',
    body,
    token,
    root = false,
    timeoutMs = REQUEST_TIMEOUT_MS,
    signal,
  } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const forwardAbort = () => controller.abort();
  signal?.addEventListener('abort', forwardAbort);

  try {
    const response = await fetch(apiUrl(path, root), {
      method,
      headers: {
        Accept: 'application/json',
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });

    const payload = await readPayload(response);

    if (!response.ok) throw buildApiError(response.status, payload);
    return payload as T;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', forwardAbort);
  }
}

async function readPayload(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  const text = await response.text().catch(() => '');
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    // 后端理论上只回 JSON；真回了 HTML（比如代理错误页）就别假装能解析
    return text;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function defaultCodeFor(status: number): string {
  switch (status) {
    case 401:
      return 'unauthorized';
    case 403:
      return 'permission_denied';
    case 404:
      return 'not_found';
    case 409:
      return 'conflict';
    case 422:
      return 'validation_error';
    default:
      return 'http_error';
  }
}

function buildApiError(status: number, payload: unknown): ApiError {
  if (isRecord(payload)) {
    const envelope = payload as Partial<ErrorResponse>;
    const hasEnvelope = typeof envelope.code === 'string' || typeof envelope.message === 'string';
    if (hasEnvelope) {
      return new ApiError(
        status,
        envelope.code ?? defaultCodeFor(status),
        envelope.message ?? `HTTP ${status}`,
        envelope.detail ?? null,
      );
    }

    // FastAPI 默认的 422：detail 是一个对象数组
    const detail = payload.detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      const loc = isRecord(first) && Array.isArray(first.loc) ? first.loc : [];
      const field = loc.filter((part) => part !== 'body').join('.');
      const reason =
        isRecord(first) && typeof first.msg === 'string' ? first.msg : 'validation failed';
      return new ApiError(
        status,
        'validation_error',
        field ? `${field}: ${reason}` : reason,
        detail,
      );
    }
  }

  return new ApiError(status, defaultCodeFor(status), `HTTP ${status}`, payload ?? null);
}

/**
 * 把任意异常翻译成**给用户看的一句中文**。
 *
 * 后端的 `message` 是英文（`"plan not found"`），所以这里按 `code` 优先讲人话，
 * 拿不准的才回落到后端原文 —— 不编造，也不把英文原文怼到用户脸上。
 */
export function describeApiError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'unauthorized':
        return '登录状态已失效，请重新登录。';
      case 'permission_denied':
        return '这个计划不属于当前账号。';
      case 'not_found':
        return '后端找不到这条数据，可能已经被删掉了。';
      case 'conflict':
        return error.message.includes('email') ? '这个邮箱已经注册过了。' : '数据冲突，刷新后再试一次。';
      case 'replan_not_eligible': {
        /*
         * 实测 409 的 body 是完整信封，而且 `detail` 里就是一份
         * `ReplanEligibilityRead`（含 `next_eligible_at`）。把具体的可再排时间
         * 说出来，比"还没到时间"有用得多。
         */
        const detail = error.detail;
        const nextAt =
          typeof detail === 'object' && detail !== null && 'next_eligible_at' in detail
            ? (detail as { next_eligible_at?: unknown }).next_eligible_at
            : null;
        const readable = typeof nextAt === 'string' ? formatDateTimeLabel(nextAt) : '';
        return readable
          ? `计划刚重排过，要到 ${readable} 才能再排一次。`
          : '计划刚重排过，还没到可以再排的时间。';
      }
      case 'validation_error':
        return `提交的内容后端不接受：${error.message}`;
      case 'http_error':
        return `后端返回了 ${error.status}。`;
      default:
        return error.message || `请求失败（HTTP ${error.status}）。`;
    }
  }

  if (error instanceof Error) {
    if (error.name === 'AbortError') return '请求超时了，检查一下是不是和后端在同一网络？';
    return '连不上后端。确认后端在跑、并且和这台设备在同一局域网。';
  }

  return '出了点问题，再试一次。';
}
