import { IBMPlexMono_400Regular } from '@expo-google-fonts/ibm-plex-mono/400Regular';
import { IBMPlexMono_500Medium } from '@expo-google-fonts/ibm-plex-mono/500Medium';
import { IBMPlexMono_600SemiBold } from '@expo-google-fonts/ibm-plex-mono/600SemiBold';
import { useFonts } from 'expo-font';
import { Slot } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';

import { FeedbackGate } from '@/components/feedback/feedback-gate';
import { AppShell } from '@/components/shell/app-shell';
import { ErrorState, LoadingState } from '@/components/ui/states';
import { Space } from '@/constants/tokens';
import { PlanProvider, usePlan } from '@/state/plan';
import { ProfileProvider } from '@/state/profile';
import { ScheduleProvider } from '@/state/schedule';
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
        <PlanProvider>
          <ProfileProvider>
            <ScheduleProvider>
              <RootShell />
            </ScheduleProvider>
          </ProfileProvider>
        </PlanProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}

function RootShell() {
  const { colors, resolved } = useTheme();
  const { mode, loading, error, retryConnection } = usePlan();
  const insets = useSafeAreaInsets();
  // The first connect owns the full screen. Later refreshes keep the current
  // page mounted and update it in place.
  const [booted, setBooted] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- flip once, after the first load settles
    if (mode === 'api' && !loading) setBooted(true);
  }, [mode, loading]);

  const safePadding = {
    paddingTop: insets.top + Space.xl,
    paddingBottom: insets.bottom + Space.xl,
    paddingLeft: insets.left + Space.xl,
    paddingRight: insets.right + Space.xl,
  };

  if (mode === 'api' && error) {
    return (
      <View style={[styles.center, safePadding, { backgroundColor: colors.paper }]}>
        <View style={styles.panel}>
          <ErrorState
            title="连不上后端"
            body={`${error} 检查那台电脑是否在跑后端，以及是否同一局域网。`}
            onRetry={retryConnection}
          />
        </View>
      </View>
    );
  }

  if (mode === 'api' && loading && !booted) {
    return (
      <View style={[styles.center, safePadding, { backgroundColor: colors.paper }]}>
        <LoadingState label="正在连接后端…" />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.paper }}>
      <StatusBar style={resolved === 'dark' ? 'light' : 'dark'} />
      <AppShell>
        <Slot />
      </AppShell>
      <FeedbackGate />
    </View>
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
