/**
 * 后端地址与请求参数。
 *
 * ## 地址怎么来的
 *
 * 后端跑在**局域网另一台机器**：`http://192.168.9.67:8000`（实测可直连，
 * CORS 是 `*`，所以 Web / 真机都不需要额外配置）。
 *
 * 要换地址就在 `damn-app/.env` 里写：
 *
 * ```
 * EXPO_PUBLIC_API_BASE_URL=http://192.168.1.10:8000
 * ```
 *
 * ⚠️ `EXPO_PUBLIC_*` 是**构建期内联**的，改完必须重启 `expo start`（加 `--clear`），
 * 热更新不会生效。
 *
 * ## 各平台的坑
 *
 * - 真机 / 局域网：直接用上面的 IP，只要手机和那台机器在同一网段。
 * - Android 模拟器：`localhost` 指模拟器自己，要用 `http://10.0.2.2:8000`。
 * - Web：浏览器直连，靠后端 CORS 放行（实测 `access-control-allow-origin: *`，没问题）。
 */

/** 没有 `.env` 时的兜底：局域网那台后端。 */
const FALLBACK_BASE_URL = 'http://192.168.9.67:8000';

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

export const API_BASE_URL = stripTrailingSlash(
  process.env.EXPO_PUBLIC_API_BASE_URL?.trim() || FALLBACK_BASE_URL,
);

/** 除 `/health` 外的所有接口都在这个前缀下。 */
export const API_PREFIX = '/api/v1';

/**
 * 普通读写接口的超时。
 *
 * 30 秒是**实测调出来的**，不是拍的：在那台局域网后端上遇到过 `/health` 单次要
 * 18.3 秒才返回的情况（同时 `/api/v1/plans` 未过鉴权时 0.36 秒 —— 说明网络不慢，
 * 是那台机器上的服务在争用）。原来的 20 秒会把这种本来能成功的请求误判成超时。
 *
 * 代价是出错时用户要多等一会儿；考虑到这是一次本地/局域网的开发后端，
 * 宁可等，也不要报一个假超时。
 */
export const REQUEST_TIMEOUT_MS = 30_000;

/**
 * 计划生成 / 重排的超时。
 *
 * 实测 `POST /plans/generate` 同步跑完约 1.5 s（后端把 LangGraph 跑完才返回），
 * 但换机器或计划变大时会变慢，这里给足 3 分钟。
 */
export const GENERATE_TIMEOUT_MS = 180_000;
