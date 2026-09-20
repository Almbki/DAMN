/**
 * 一点点持久化：**JWT 和"上次看的计划 id"**，就这两样。
 *
 * ## 为什么分平台
 *
 * - 原生：`expo-secure-store` → Keychain / Android Keystore，JWT 不该明文落盘。
 * - Web：`localStorage`。`expo-secure-store` 在 Web 上是个空 stub
 *   （`ExpoSecureStore.web.js` 只有 `export default {}`），调它的方法会炸。
 *
 * ## 原生必须重新构建
 *
 * `expo-secure-store` 是**原生模块**。装完之后：
 * - Expo Go 里直接可用（Expo Go 自带）；
 * - 自己构建的 dev build / APK **必须重新构建**才会带上它
 *   （`npx expo run:android` 或重新出包）。
 *
 * 没重建时的行为是这里最要紧的一处设计：`requireNativeModule('ExpoSecureStore')`
 * 会在**模块加载时**抛错。所以下面一律用**动态 `import()`** 而不是静态 import ——
 * 静态 import 会让这个异常发生在 App 启动阶段，直接白屏；动态 import 则变成一个
 * 可以被 catch 的 rejection，于是降级为"令牌只在内存里 + 一条警告"，**APP 照样能开**。
 */

import { Platform } from 'react-native';

const TOKEN_KEY = 'damn.auth.token';
const PLAN_ID_KEY = 'damn.plan.id';

/** 原生模块缺失时的兜底：令牌只活在这一个进程里。 */
const memoryFallback = new Map<string, string>();
let warnedAboutFallback = false;

function warnFallback(reason: string): void {
  if (warnedAboutFallback) return;
  warnedAboutFallback = true;
  console.warn(
    `[storage] expo-secure-store 不可用（${reason}），登录状态只保存在内存里；` +
      '原生端请重新构建 dev build（npx expo run:android）以启用安全存储。',
  );
}

async function readRaw(key: string): Promise<string | null> {
  if (Platform.OS === 'web') {
    try {
      return globalThis.localStorage?.getItem(key) ?? null;
    } catch {
      // 隐私模式 / 禁用存储
      return memoryFallback.get(key) ?? null;
    }
  }

  try {
    const SecureStore = await import('expo-secure-store');
    return await SecureStore.getItemAsync(key);
  } catch (error) {
    warnFallback(error instanceof Error ? error.message : String(error));
    return memoryFallback.get(key) ?? null;
  }
}

async function writeRaw(key: string, value: string): Promise<void> {
  if (Platform.OS === 'web') {
    try {
      globalThis.localStorage?.setItem(key, value);
      return;
    } catch {
      memoryFallback.set(key, value);
      return;
    }
  }

  try {
    const SecureStore = await import('expo-secure-store');
    await SecureStore.setItemAsync(key, value);
  } catch (error) {
    warnFallback(error instanceof Error ? error.message : String(error));
    memoryFallback.set(key, value);
  }
}

async function removeRaw(key: string): Promise<void> {
  memoryFallback.delete(key);
  if (Platform.OS === 'web') {
    try {
      globalThis.localStorage?.removeItem(key);
    } catch {
      // 本来就删不掉，忽略
    }
    return;
  }

  try {
    const SecureStore = await import('expo-secure-store');
    await SecureStore.deleteItemAsync(key);
  } catch (error) {
    warnFallback(error instanceof Error ? error.message : String(error));
  }
}

/* ------------------------------------------------------------------- token */

export async function readToken(): Promise<string | null> {
  return readRaw(TOKEN_KEY);
}

export async function writeToken(token: string): Promise<void> {
  await writeRaw(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await removeRaw(TOKEN_KEY);
}

/* ----------------------------------------------------------------- plan id */

/**
 * 记住"上次打开的哪个计划"。
 *
 * 不做这个的话每次冷启动都得先 `GET /plans` 再挑一个；有了它就能直接
 * `GET /plans/{id}`，列表请求降级成"校验 + 兜底"。
 */
export async function readStoredPlanId(): Promise<number | null> {
  const raw = await readRaw(PLAN_ID_KEY);
  if (!raw) return null;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

export async function writeStoredPlanId(planId: number | null): Promise<void> {
  if (planId === null) {
    await removeRaw(PLAN_ID_KEY);
    return;
  }
  await writeRaw(PLAN_ID_KEY, String(planId));
}
