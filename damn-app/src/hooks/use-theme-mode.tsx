import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { Appearance, Platform } from 'react-native';

import { useColorScheme } from '@/hooks/use-color-scheme';

/** 三态：跟系统 / 强制浅色 / 强制深色。 */
export type ThemeMode = 'system' | 'light' | 'dark';
export type Scheme = 'light' | 'dark';

const STORAGE_KEY = 'damn.themeMode';
/** URL 覆盖参数。**只走 query，不落存储** —— 它必须是一次性的，否则截图脚本留下的
 *  参数会永久改变你本地的主题。对分享链接也友好：`?theme=dark` 直接给人看深色。 */
const QUERY_KEY = 'theme';

type ThemeModeContextValue = {
  /** 用户选的三态 */
  mode: ThemeMode;
  /** 当前真正生效的明暗 */
  scheme: Scheme;
  /** 切换。传 'system' 表示跟回系统 */
  setMode: (mode: ThemeMode) => void;
  /** 在 浅 → 深 → 跟系统 之间轮转（给按钮用） */
  cycle: () => void;
};

const ThemeModeContext = createContext<ThemeModeContextValue | null>(null);

function readStoredMode(): ThemeMode {
  if (Platform.OS !== 'web' || typeof window === 'undefined') return 'system';
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  } catch {
    // 隐私模式 / 禁用存储：静默退回跟系统
  }
  return 'system';
}

function readQueryMode(): ThemeMode | null {
  if (Platform.OS !== 'web' || typeof window === 'undefined') return null;
  try {
    const value = new URLSearchParams(window.location.search).get(QUERY_KEY);
    if (value === 'light' || value === 'dark' || value === 'system') return value;
  } catch {
    // 忽略
  }
  return null;
}

/**
 * ⚠️ **这个字符串是本文件最容易搞崩 App 的地方，改动前先读完这段。**
 *
 * `Appearance.setColorScheme` 的**原生实现**（RN 0.86 Android）是：
 *
 * ```kotlin
 * public override fun setColorScheme(style: String) {   // ← 非空 String
 *   when (style) {
 *     "dark" -> AppCompatDelegate.setDefaultNightMode(MODE_NIGHT_YES)
 *     "light" -> AppCompatDelegate.setDefaultNightMode(MODE_NIGHT_NO)
 *     "unspecified" -> AppCompatDelegate.setDefaultNightMode(MODE_NIGHT_FOLLOW_SYSTEM)
 *   }
 * }
 * ```
 *
 * 三个合法值就是 `'dark' | 'light' | 'unspecified'`（与 TS 的 `ColorSchemeName` 一致）。
 *
 * **踩过的坑**：曾经写成 `setColorScheme(mode === 'system' ? null : mode)` 并用
 * `as ColorSchemeName` 把类型断言糊过去 —— 类型检查通过，运行时给原生模块传了
 * `null`，Kotlin 非空参数直接抛异常，**手机一打开就红屏**：
 *
 * ```
 * Parameter specified as non-null is null: method
 * com.facebook.react.modules.appearance.AppearanceModule.setColorScheme, parameter style
 * ```
 *
 * 传 `undefined` 也一样崩（跨桥会变成 `null`）。**"跟系统"的正确值是字符串
 * `'unspecified'`。** 不许再用类型断言绕编译错误。
 */
const NATIVE_SYSTEM = 'unspecified' as const;

/** 把三态翻成原生认识的字符串。**只可能返回三个合法值之一。** */
function toNativeScheme(mode: ThemeMode): 'light' | 'dark' | 'unspecified' {
  if (mode === 'light') return 'light';
  if (mode === 'dark') return 'dark';
  return NATIVE_SYSTEM;
}

/**
 * 手动明暗切换的 Provider。
 *
 * ## 为什么不能只靠 `useColorScheme()`
 *
 * `useColorScheme()` 永远返回系统值，没有"用户说了算"的位置。所以这里自己维护
 * 三态，再把结果**广播**给两层：
 *
 * - Context 覆盖本项目组件（`useScheme()` 优先读它）；
 * - `Appearance.setColorScheme()` 通知原生层，让导航容器、状态栏、键盘、滚动条
 *   一起变 —— 这是 RN 官方的做法，不是 hack。
 *
 * ## 优先级
 *
 * `URL query ?theme=` > `localStorage` > 跟系统。
 *
 * query 放最前是为了让**无头浏览器截图**能确定性取值 —— 浏览器标志
 * （`--force-dark-mode`）实测不改变 `prefers-color-scheme`，会污染验收结果。
 */
export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const system = useColorScheme();
  const [mode, setModeState] = useState<ThemeMode>(() => readQueryMode() ?? readStoredMode());

  // 挂载后再读一次 query：静态渲染阶段没有 window，首帧只能按存储值渲染
  useEffect(() => {
    const fromQuery = readQueryMode();
    if (fromQuery) setModeState(fromQuery);
  }, []);

  useEffect(() => {
    if (Platform.OS === 'web') return;
    // 只传三个合法字符串之一。兜底 try/catch 是**防御性的**：万一将来的 RN
    // 版本改了签名，也不该让整个 App 起不来（不过正确性靠上面的 toNativeScheme，
    // 不靠这个 catch）。
    try {
      Appearance.setColorScheme(toNativeScheme(mode));
    } catch (error) {
      console.warn('[theme] 无法把外观同步给原生层，仅本 App 内生效：', error);
    }
  }, [mode]);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    if (Platform.OS === 'web' && typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // 存不了就算了，本次会话内仍然生效
      }
    }
  }, []);

  // `useColorScheme()` 可能返回 'unspecified'（以及历史实现里的 null/undefined），
  // 一律归一到 'light'。
  const scheme: Scheme =
    mode === 'system' ? (system === 'dark' ? 'dark' : 'light') : mode;

  const cycle = useCallback(() => {
    // 浅 → 深 → 跟系统 → 浅
    setMode(mode === 'light' ? 'dark' : mode === 'dark' ? 'system' : 'light');
  }, [mode, setMode]);

  const value = useMemo(
    () => ({ mode, scheme, setMode, cycle }),
    [mode, scheme, setMode, cycle],
  );

  return <ThemeModeContext.Provider value={value}>{children}</ThemeModeContext.Provider>;
}

/**
 * 取当前主题模式。**必须在 `<ThemeModeProvider>` 内使用**。
 *
 * 组件要拿颜色请用 `useTheme()`（它已经接上了这个 Provider），
 * 只有做"切换按钮"这类 UI 时才需要直接用这个 hook。
 */
export function useThemeMode(): ThemeModeContextValue {
  const ctx = useContext(ThemeModeContext);
  if (!ctx) {
    throw new Error('useThemeMode 必须在 <ThemeModeProvider> 内使用（见 app/_layout.tsx）');
  }
  return ctx;
}

/**
 * 不抛错的版本。给 `useScheme()` 用 —— 组件在没有 Provider 时应该退回系统主题，
 * 而不是整个界面炸掉（比如某个组件被单独渲染在测试或预览里）。
 */
export function useThemeModeSafe(): ThemeModeContextValue | null {
  return useContext(ThemeModeContext);
}

/** 给切换按钮用的文案。 */
export function themeModeLabel(mode: ThemeMode): string {
  return mode === 'light' ? '浅色' : mode === 'dark' ? '深色' : '跟系统';
}
