import { IBMPlexMono_400Regular } from '@expo-google-fonts/ibm-plex-mono/400Regular';
import { IBMPlexMono_500Medium } from '@expo-google-fonts/ibm-plex-mono/500Medium';
import { IBMPlexMono_600SemiBold } from '@expo-google-fonts/ibm-plex-mono/600SemiBold';
import { useFonts } from 'expo-font';
import { Redirect, Slot, usePathname, type Href } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View } from 'react-native';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';

import { dataSource } from '@/api/config';
import { FeedbackGate } from '@/components/feedback/feedback-gate';
import { AppShell } from '@/components/shell/app-shell';
import { ErrorState, LoadingState } from '@/components/ui/states';
import { resolveGuardState } from '@/domain/auth';
import { Space } from '@/constants/tokens';
import { PlanProvider } from '@/state/plan';
import { ProfileProvider } from '@/state/profile';
import { ScheduleProvider } from '@/state/schedule';
import { SessionProvider, useSession } from '@/state/session';
import { ThemeProvider, useTheme } from '@/state/theme';

export default function RootLayout() {
  // The Latin/CJK body stays on the system stack; only the time numerals load a
  // face (IBM Plex Mono), so a slow font fetch never blocks the layout.
  useFonts({
    IBMPlexMono_400Regular,
    IBMPlexMono_500Medium,
    IBMPlexMono_600SemiBold,
  });

  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <SessionProvider>
          <RootRouter />
        </SessionProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}

function RootRouter() {
  const { colors, resolved } = useTheme();
  const session = useSession();
  const pathname = usePathname();
  const insets = useSafeAreaInsets();
  const isAuthRoute = pathname === '/login' || pathname === '/register';
  const guard = resolveGuardState({
    status: session.status,
    dataSource,
    hasTrait: Boolean(session.user?.trait_profile),
  });

  const safePadding = {
    paddingTop: insets.top + Space.xl,
    paddingBottom: insets.bottom + Space.xl,
    paddingLeft: insets.left + Space.xl,
    paddingRight: insets.right + Space.xl,
  };

  if (guard === 'booting') {
    return (
      <View style={[styles.center, safePadding, { backgroundColor: colors.paper }]}>
        <LoadingState label="正在恢复登录状态…" />
      </View>
    );
  }

  if (guard === 'error') {
    return (
      <View style={[styles.center, safePadding, { backgroundColor: colors.paper }]}>
        <View style={styles.panel}>
          <ErrorState
            title="连不上后端"
            body={`${session.error ?? '请求失败'} 检查后端是否在运行，以及前端 API 地址是否正确。`}
            onRetry={session.retry}
          />
        </View>
      </View>
    );
  }

  if (guard === 'unauthenticated') {
    if (!isAuthRoute) return <Redirect href={'/login' as Href} />;
    return (
      <View style={{ flex: 1, backgroundColor: colors.paper }}>
        <StatusBar style={resolved === 'dark' ? 'light' : 'dark'} />
        <Slot />
      </View>
    );
  }

  if (guard === 'onboarding' && pathname !== '/assessment') {
    return <Redirect href="/assessment" />;
  }

  // Authenticated and onboarded: Login/Register are no longer valid.
  if (guard === 'ready' && isAuthRoute) return <Redirect href="/" />;

  return (
    <PlanProvider>
      <ProfileProvider>
        <ScheduleProvider>
          <View style={{ flex: 1, backgroundColor: colors.paper }}>
            <StatusBar style={resolved === 'dark' ? 'light' : 'dark'} />
            <AppShell>
              <Slot />
            </AppShell>
            <FeedbackGate />
          </View>
        </ScheduleProvider>
      </ProfileProvider>
    </PlanProvider>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  panel: {
    width: '100%',
    maxWidth: 520,
  },
});