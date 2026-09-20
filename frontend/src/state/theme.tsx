import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from 'react';
import { Platform, useColorScheme } from 'react-native';

import { Palette, type ThemeColors, type ThemeName } from '@/constants/tokens';

export type ThemeMode = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'damn.theme.mode';
const ORDER: ThemeMode[] = ['light', 'dark', 'system'];
const isWeb = Platform.OS === 'web';

type Listener = () => void;
const listeners = new Set<Listener>();

/**
 * On web the source of truth is localStorage; on native there is no
 * localStorage, so a module-level value stands in. Both are exposed through the
 * same snapshot so the provider needs no setState-in-effect on either platform.
 */
let memoryMode: ThemeMode = 'light';

function isMode(value: string | null | undefined): value is ThemeMode {
  return value === 'light' || value === 'dark' || value === 'system';
}

function readStoredMode(): ThemeMode {
  if (!isWeb) return memoryMode;
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (isMode(value)) return value;
  } catch {
    // localStorage can be unavailable (private mode / blocked). Default light.
  }
  return 'light';
}

function writeStoredMode(mode: ThemeMode) {
  memoryMode = mode;
  if (!isWeb) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    // Ignore persistence failures.
  }
}

function notify() {
  listeners.forEach((listener) => listener());
}

/** Subscribe to same-tab writes plus cross-tab storage events (web only). */
function subscribe(listener: Listener) {
  listeners.add(listener);
  if (!isWeb) return () => listeners.delete(listener);

  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY) listener();
  };
  window.addEventListener('storage', onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener('storage', onStorage);
  };
}

function getServerSnapshot(): ThemeMode {
  return 'light';
}

/**
 * Screenshot/QA override: `?theme=light|dark|system` (web only). It wins over
 * storage and is not persisted, so visual captures are deterministic while the
 * real toggle path is still exercised.
 */
function getUrlOverride(): ThemeMode | null {
  if (!isWeb) return null;
  try {
    const value = new URLSearchParams(window.location.search).get('theme');
    return isMode(value) ? value : null;
  } catch {
    return null;
  }
}

function getActiveSnapshot(): ThemeMode {
  return getUrlOverride() ?? readStoredMode();
}

type ThemeContextValue = {
  mode: ThemeMode;
  resolved: ThemeName;
  colors: ThemeColors;
  setMode: (mode: ThemeMode) => void;
  cycleMode: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const system = useColorScheme();
  // Reads the persisted/overridden mode without a hydration mismatch and
  // without a setState-in-effect.
  const mode = useSyncExternalStore(subscribe, getActiveSnapshot, getServerSnapshot);

  const resolved: ThemeName = mode === 'system' ? (system === 'dark' ? 'dark' : 'light') : mode;

  const setMode = useCallback((next: ThemeMode) => {
    writeStoredMode(next);
    notify();
  }, []);

  const cycleMode = useCallback(() => {
    const current = getActiveSnapshot();
    setMode(ORDER[(ORDER.indexOf(current) + 1) % ORDER.length]);
  }, [setMode]);

  // Keep the browser's own chrome (scrollbars, form controls) in sync on web.
  useEffect(() => {
    if (isWeb && typeof document !== 'undefined') {
      document.documentElement.style.colorScheme = resolved;
    }
  }, [resolved]);

  const value = useMemo<ThemeContextValue>(
    () => ({ mode, resolved, colors: Palette[resolved], setMode, cycleMode }),
    [mode, resolved, setMode, cycleMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used inside <ThemeProvider>');
  return context;
}
