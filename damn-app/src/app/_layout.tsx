import { DarkTheme, DefaultTheme, Slot, ThemeProvider, usePathname, type Theme } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect, useRef } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { AuthScreen } from '@/components/auth-screen';
import { ErrorBoundary } from '@/components/error-boundary';
import { MonoText } from '@/components/mono';
import { NavRail } from '@/components/nav-rail';
import { MonoSpace } from '@/constants/mono';
import { TABS } from '@/constants/tabs';
import { useIsWide, useScheme } from '@/hooks/use-theme';
import { useMono } from '@/hooks/use-mono';
import { ThemeModeProvider } from '@/hooks/use-theme-mode';
import { PlanProvider } from '@/plan/plan-provider';
import { SessionProvider, useSession } from '@/session/session-provider';

// 启动图由我们自己控制隐藏时机。只在原生上接管 —— Web 上没有启动图。
if (Platform.OS !== 'web') {
  SplashScreen.preventAutoHideAsync().catch(() => {
    // 拿不到原生模块时不要炸掉整个 App
  });
}

/** 兜底隐藏启动图的上限，防止 onLayout 意外不触发时永远停在启动图。 */
const SPLASH_FALLBACK_MS = 1500;

/**
 * 根布局。
 *
 * ## 三层包裹（顺序不能换）
 *
 * ```
 * ThemeModeProvider      ← 主题最外层：useScheme() 要从它读手动切换
 *   SessionProvider      ← 会话：有没有 token / 是谁
 *     PlanProvider       ← 计划：只在登录后挂，登出即销毁
 *       顶部标题 + <Slot/> + 导航
 * ```
 *
 * ## 登录门
 *
 * 没登录就**不渲染 Slot**，直接渲染 `AuthScreen`。5 个页面里一句「没登录怎么办」
 * 都不用写，深链接也不会先闪一下页面。
 *
 * ## 响应式（宽屏侧栏 / 窄屏底栏）
 *
 * 用 `useIsWide()`：静态渲染阶段强制按窄屏，挂载后再切 —— 否则服务端与客户端
 * 结构不一致会 hydration 崩溃。
 */
export default function RootLayout() {
  return (
    <ThemeModeProvider>
      <SessionProvider>
        <RootLayoutInner />
      </SessionProvider>
    </ThemeModeProvider>
  );
}

function RootLayoutInner() {
  const scheme = useScheme();
  const c = useMono();
  const isWide = useIsWide();
  const { status } = useSession();
  const pathname = usePathname();

  const splashHidden = useRef(false);

  const hideSplash = () => {
    if (Platform.OS === 'web' || splashHidden.current) return;
    splashHidden.current = true;
    SplashScreen.hideAsync().catch(() => {
      // 隐藏失败也不能让界面卡住
    });
  };

  useEffect(() => {
    const timer = setTimeout(hideSplash, SPLASH_FALLBACK_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const base = scheme === 'dark' ? DarkTheme : DefaultTheme;

  // 把黑白 token 喂给路由自带主题，避免导航容器白闪。
  const navTheme: Theme = {
    ...base,
    colors: {
      ...base.colors,
      primary: c.strong,
      background: c.bg,
      card: c.panel,
      text: c.text,
      border: c.border,
    },
  };

  // 还在读本地令牌 / 验活：什么都不承诺，只占个位（原生上启动图也还盖着）
  if (status === 'restoring') {
    return (
      <View style={[styles.center, { backgroundColor: c.bg }]}>
        <MonoText type="sub" color="faint">
          正在恢复登录状态…
        </MonoText>
      </View>
    );
  }

  // 登录门
  if (status === 'signedOut') {
    return <AuthScreen />;
  }

  return (
    <PlanProvider>
      <ThemeProvider value={navTheme}>
        <View
          style={[styles.root, { flexDirection: isWide ? 'row' : 'column', backgroundColor: c.bg }]}
          onLayout={hideSplash}>
          {isWide ? <NavRail placement="rail" /> : null}

          <View style={styles.content}>
            <Header title={titleFor(pathname)} />
            <View style={styles.body}>
              <ErrorBoundary>
                <Slot />
              </ErrorBoundary>
            </View>
          </View>

          {!isWide ? <NavRail placement="bottom" /> : null}
        </View>
      </ThemeProvider>
    </PlanProvider>
  );
}

/** 顶部标题栏。文案来自当前路由对应的 tab，找不到就回到品牌名。 */
function Header({ title }: { title: string }) {
  const c = useMono();
  const insets = useSafeAreaInsets();

  return (
    <View
      style={[
        styles.header,
        {
          backgroundColor: c.bg,
          borderBottomColor: c.border,
          paddingTop: insets.top + MonoSpace.four,
        },
      ]}>
      <MonoText type="display">{title}</MonoText>
    </View>
  );
}

function titleFor(pathname: string): string {
  const normalized = pathname.replace(/\/+$/, '') || '/';
  const tab = TABS.find((item) => (String(item.href).replace(/\/+$/, '') || '/') === normalized);
  return tab?.title ?? 'DAMN';
}

const styles = StyleSheet.create({
  root: { flex: 1, alignItems: 'stretch' },
  content: { flex: 1, alignSelf: 'stretch' },
  body: { flex: 1 },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: MonoSpace.five,
  },
  header: {
    paddingHorizontal: MonoSpace.six,
    paddingBottom: MonoSpace.four,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
});
