/**
 * 会话层：JWT 从哪来、放哪、什么时候作废。
 *
 * ## 一个刻意的设计：token 放在 state 里，不放全局变量
 *
 * 所有需要鉴权的调用都从 `useSession()` 取 token 显式传给接口函数。好处是
 * **登出后没有任何闭包还攥着旧 token**，不会出现"退了还在偷偷请求"的情况。
 *
 * ## 冷启动为什么要打一次 `/users/me`
 *
 * 本地存的是 JWT，但 JWT 可能已经过期（`expires_in` 7 天，**后端没有 refresh**）。
 * 所以启动时先验活：
 *  - 401 → 令牌确实废了，清掉回登录页；
 *  - 其它错误（比如后端没开、不在同一网段）→ **不动令牌**，保持登录态让页面去报错。
 *    断个网就把人踢回登录页是很讨厌的行为。
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { ApiError } from '@/api/client';
import * as endpoints from '@/api/endpoints';
import { clearToken, readToken, writeToken } from '@/api/storage';
import type { UserRead } from '@/api/types';

export type SessionStatus =
  /** 正在读本地令牌 / 验活，先别渲染页面 */
  | 'restoring'
  | 'signedOut'
  | 'signedIn';

export type SessionValue = {
  status: SessionStatus;
  user: UserRead | null;
  /** 仅在 `status === 'signedIn'` 时有值 */
  token: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, displayName?: string) => Promise<void>;
  signOut: () => Promise<void>;
  /** 重新拉一次用户资料（设置页保存后调用，让界面立刻反映新值）。 */
  refreshUser: () => Promise<void>;
};

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>('restoring');
  const [user, setUser] = useState<UserRead | null>(null);
  const [token, setToken] = useState<string | null>(null);

  // 冷启动：读令牌 → 验活
  useEffect(() => {
    let cancelled = false;

    (async () => {
      const stored = await readToken();
      if (cancelled) return;

      if (!stored) {
        setStatus('signedOut');
        return;
      }

      try {
        const me = await endpoints.getMe(stored);
        if (cancelled) return;
        setToken(stored);
        setUser(me);
        setStatus('signedIn');
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && error.isUnauthorized) {
          await clearToken();
          setStatus('signedOut');
          return;
        }
        // 网络问题：保留令牌和登录态，让页面自己显示"连不上后端"
        setToken(stored);
        setStatus('signedIn');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const adoptToken = useCallback(async (accessToken: string) => {
    await writeToken(accessToken);
    // 登录这一步已经成功了 —— 先落地会话，再去取用户资料。
    setToken(accessToken);
    setStatus('signedIn');
    try {
      setUser(await endpoints.getMe(accessToken));
    } catch (error) {
      /*
       * 只有 401 说明令牌真有问题（正常不该发生），照抛让用户重来；
       * 其它情况（后端刚重启、网络抖）不该把已经登录成功的人堵在登录页：
       * 会话保持，用户资料留空，计划层会把"连不上后端"显示出来。
       */
      if (error instanceof ApiError && error.isUnauthorized) {
        await clearToken();
        setToken(null);
        setStatus('signedOut');
        throw error;
      }
    }
  }, []);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const result = await endpoints.login({ email: email.trim(), password });
      await adoptToken(result.access_token);
    },
    [adoptToken],
  );

  const signUp = useCallback(
    async (email: string, password: string, displayName?: string) => {
      await endpoints.register({
        email: email.trim(),
        password,
        display_name: displayName?.trim() || undefined,
      });
      // 注册接口不返回令牌，直接接着登录 —— 少让用户再填一次密码
      await signIn(email, password);
    },
    [signIn],
  );

  const signOut = useCallback(async () => {
    await clearToken();
    setToken(null);
    setUser(null);
    setStatus('signedOut');
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) return;
    try {
      setUser(await endpoints.getMe(token));
    } catch (error) {
      // 只有 401 说明令牌确实废了；其它情况（网络抖动）保持现状，不把人踢出去
      if (error instanceof ApiError && error.isUnauthorized) {
        await clearToken();
        setToken(null);
        setUser(null);
        setStatus('signedOut');
      }
    }
  }, [token]);

  const value = useMemo<SessionValue>(
    () => ({ status, user, token, signIn, signUp, signOut, refreshUser }),
    [status, user, token, signIn, signUp, signOut, refreshUser],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error('useSession 必须在 <SessionProvider> 里使用');
  return value;
}

/**
 * 需要 token 的页面用这个。
 *
 * 拿不到 token 就抛错，而不是让页面拿 `null` 去请求 —— 那样只会得到一堆 401。
 * 调用点都在 `_layout.tsx` 的登录门之后，所以正常情况下不会触发。
 */
export function useAuthToken(): string {
  const { token, status } = useSession();
  if (!token || status !== 'signedIn') {
    throw new Error('这个页面需要登录后才能用（应当被 _layout 的登录门拦住）');
  }
  return token;
}
