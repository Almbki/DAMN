import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { isApiError, setAuthToken } from '@/api/client';
import { dataSource, devEmail, devPassword } from '@/api/config';
import { getMe, login as loginRequest, register } from '@/api/endpoints';
import type { UserRead } from '@/api/types';

type SessionStatus = 'idle' | 'loading' | 'ready' | 'error';

type SessionContextValue = {
  status: SessionStatus;
  user: UserRead | null;
  error: string | null;
  retry: () => void;
  setUser: (user: UserRead) => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

/** Silently sign in the dev account: login, else register then login. */
async function acquireToken(): Promise<void> {
  try {
    const token = await loginRequest(devEmail, devPassword);
    setAuthToken(token.access_token);
    return;
  } catch (error) {
    if (!isApiError(error) || (error.status !== 401 && error.status !== 404)) throw error;
  }

  try {
    await register({ email: devEmail, password: devPassword, display_name: '演示用户' });
  } catch (error) {
    if (!isApiError(error) || error.status !== 409) throw error;
  }

  const token = await loginRequest(devEmail, devPassword);
  setAuthToken(token.access_token);
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>(dataSource === 'api' ? 'loading' : 'idle');
  const [user, setUserState] = useState<UserRead | null>(null);
  const [error, setError] = useState<string | null>(null);

  const signIn = useCallback(async () => {
    if (dataSource !== 'api') return;
    try {
      await acquireToken();
      const me = await getMe();
      setUserState(me);
      setStatus('ready');
      setError(null);
    } catch (caught) {
      setAuthToken(null);
      setError(isApiError(caught) ? caught.message : '登录失败');
      setStatus('error');
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sign in once on mount
    void signIn();
  }, [signIn]);

  const retry = useCallback(() => {
    setStatus('loading');
    setError(null);
    void signIn();
  }, [signIn]);

  const setUser = useCallback((next: UserRead) => setUserState(next), []);

  const value = useMemo<SessionContextValue>(
    () => ({ status, user, error, retry, setUser }),
    [status, user, error, retry, setUser],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error('useSession must be used inside <SessionProvider>');
  return context;
}
