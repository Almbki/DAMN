import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { isApiError, setAuthToken, setUnauthorizedHandler } from '@/api/client';
import { dataSource, demoEmail, demoLoginEnabled, demoPassword } from '@/api/config';
import { getMe, login as loginRequest, register as registerRequest } from '@/api/endpoints';
import type { RegisterRequest, UserRead } from '@/api/types';
import type { SessionStatus } from '@/domain/auth';
import { clearUserScopedCaches } from '@/state/user-cache';

export type { SessionStatus };

type SessionContextValue = {
  status: SessionStatus;
  user: UserRead | null;
  error: string | null;
  /** Normal JWT login; throws ApiError so the login form can show the message. */
  login: (email: string, password: string) => Promise<void>;
  /** Register via the normal backend endpoint, then perform a normal login. */
  register: (input: RegisterRequest) => Promise<void>;
  logout: () => void;
  retry: () => void;
  clearError: () => void;
  setUser: (user: UserRead) => void;
  /** True only when public demo credentials are explicitly configured. */
  demoMode: boolean;
};

const SessionContext = createContext<SessionContextValue | null>(null);

function messageOf(error: unknown, fallback: string): string {
  if (isApiError(error)) return error.message;
  return fallback;
}

/**
 * Session bootstrap:
 *   stored valid token -> authenticated
 *   no/invalid token + demo credentials -> normal POST /auth/login
 *   otherwise -> unauthenticated (Login/Register)
 *
 * There is no auth bypass: demo mode uses the same JWT endpoint and dependency
 * checks as every other user.
 */
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>(
    dataSource === 'api' ? 'booting' : 'authenticated',
  );
  const [user, setUserState] = useState<UserRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const busyRef = useRef(false);
  // Mirrors the signed-in user so the stable unauthorized handler can clean up
  // the right user's local caches without re-registering.
  const userIdRef = useRef<number | null>(null);

  useEffect(() => {
    userIdRef.current = user?.id ?? null;
  }, [user]);

  const login = useCallback(async (email: string, password: string) => {
    const token = await loginRequest(email, password);
    setAuthToken(token.access_token);
    try {
      const me = await getMe();
      setUserState(me);
      setStatus('authenticated');
      setError(null);
    } catch (caught) {
      setAuthToken(null);
      throw caught;
    }
  }, []);

  const register = useCallback(
    async (input: RegisterRequest) => {
      await registerRequest(input);
      await login(input.email, input.password);
    },
    [login],
  );

  const logout = useCallback(() => {
    // Drop this user's browser-side caches before the provider unmounts; the
    // server remains the source of truth and nothing here is server data.
    clearUserScopedCaches(userIdRef.current);
    userIdRef.current = null;
    setAuthToken(null);
    setUserState(null);
    setStatus('unauthenticated');
    setError(null);
  }, []);

  const bootstrap = useCallback(async () => {
    if (dataSource !== 'api') {
      setStatus('authenticated');
      return;
    }
    if (busyRef.current) return;
    busyRef.current = true;
    setStatus('booting');
    setError(null);

    try {
      try {
        const me = await getMe();
        setUserState(me);
        setStatus('authenticated');
        return;
      } catch (caught) {
        if (!isApiError(caught) || caught.status !== 401) {
          setError(messageOf(caught, '连不上后端'));
          setStatus('error');
          return;
        }
        // Expired/invalid stored token: drop it and continue to demo/login.
        setAuthToken(null);
      }

      if (demoLoginEnabled) {
        try {
          await login(demoEmail, demoPassword);
          return;
        } catch (caught) {
          // Do not fake a session; fall back to the login screen with a safe
          // error instead of looping.
          setError(`演示账号登录失败：${messageOf(caught, '请检查后端')}`);
        }
      }
      setStatus('unauthenticated');
    } finally {
      busyRef.current = false;
    }
  }, [login]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      // A 401 must not leave the previous user's caches for the next account.
      clearUserScopedCaches(userIdRef.current);
      userIdRef.current = null;
      setAuthToken(null);
      setUserState(null);
      setStatus('unauthenticated');
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one bootstrap per mount
    void bootstrap();
  }, [bootstrap]);

  const retry = useCallback(() => {
    void bootstrap();
  }, [bootstrap]);

  const setUser = useCallback((next: UserRead) => setUserState(next), []);

  const value = useMemo<SessionContextValue>(
    () => ({
      status,
      user,
      error,
      login,
      register,
      logout,
      retry,
      clearError: () => setError(null),
      setUser,
      demoMode: dataSource === 'api' && demoLoginEnabled,
    }),
    [status, user, error, login, register, logout, retry, setUser],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error('useSession must be used inside <SessionProvider>');
  return context;
}