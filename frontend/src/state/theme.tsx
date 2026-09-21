import { createContext, useContext, useMemo } from 'react';

import { Palette, type ThemeColors, type ThemeName } from '@/constants/tokens';

/**
 * Light-only for now. The dark roles are already derived in `tokens.ts`; when
 * the theme switch comes back, this provider grows a mode + a system listener
 * and nothing downstream changes.
 */
export type ThemeMode = 'light';

type ThemeContextValue = {
  mode: ThemeMode;
  resolved: ThemeName;
  colors: ThemeColors;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const value = useMemo<ThemeContextValue>(
    () => ({ mode: 'light', resolved: 'light', colors: Palette.light }),
    [],
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used inside <ThemeProvider>');
  return context;
}
