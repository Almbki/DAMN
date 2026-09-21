import { createContext, useCallback, useContext, useMemo, useState } from 'react';

/**
 * Scheduling preferences. Set once, then always in effect: the provider sits at
 * the root, so the values survive navigation between pages (a mock of the real
 * persisted profile — no backend field exists for them yet).
 */
export type SchedulingPreferences = {
  /** 每日可投入时间（分钟） */
  dailyMinutes: number;
  /** 单日任务上限（件） */
  dailyTaskCap: number;
  /** 任务之间的缓冲时间（分钟） */
  bufferMinutes: number;
  /** 单日高认知任务上限（件） */
  highLoadCap: number;
};

export const DEFAULT_PREFERENCES: SchedulingPreferences = {
  dailyMinutes: 240,
  dailyTaskCap: 6,
  bufferMinutes: 15,
  highLoadCap: 2,
};

type PreferencesContextValue = {
  preferences: SchedulingPreferences;
  setPreference: (key: keyof SchedulingPreferences, value: number) => void;
  reset: () => void;
};

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const [preferences, setPreferences] = useState<SchedulingPreferences>(DEFAULT_PREFERENCES);

  const setPreference = useCallback((key: keyof SchedulingPreferences, value: number) => {
    setPreferences((prev) => ({ ...prev, [key]: value }));
  }, []);

  const reset = useCallback(() => setPreferences(DEFAULT_PREFERENCES), []);

  const value = useMemo<PreferencesContextValue>(
    () => ({ preferences, setPreference, reset }),
    [preferences, setPreference, reset],
  );

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences(): PreferencesContextValue {
  const context = useContext(PreferencesContext);
  if (!context) throw new Error('usePreferences must be used inside <PreferencesProvider>');
  return context;
}
