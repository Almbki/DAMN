import { IBMPlexMono_400Regular } from '@expo-google-fonts/ibm-plex-mono/400Regular';
import { IBMPlexMono_500Medium } from '@expo-google-fonts/ibm-plex-mono/500Medium';
import { IBMPlexMono_600SemiBold } from '@expo-google-fonts/ibm-plex-mono/600SemiBold';
import { useFonts } from 'expo-font';
import { Slot } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View } from 'react-native';

import { AppShell } from '@/components/shell/app-shell';
import { ErrorState, LoadingState } from '@/components/ui/states';
import { Space } from '@/constants/tokens';
import { PlanProvider, usePlan } from '@/state/plan';
import { ProfileProvider } from '@/state/profile';
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
    <ThemeProvider>
      <PlanProvider>
        <ProfileProvider>
          <RootShell />
        </ProfileProvider>
      </PlanProvider>
    </ThemeProvider>
  );
}

function RootShell() {
  const { colors, resolved } = useTheme();
  const { mode, loading, error, refresh } = usePlan();

  if (mode === 'api' && error) {
    return (
      <View style={[styles.center, { backgroundColor: colors.paper }]}>
        <View style={styles.panel}>
          <ErrorState
            title="连不上后端"
            body={`${error} 检查那台电脑是否在跑后端，以及是否同一局域网。`}
            onRetry={refresh}
          />
        </View>
      </View>
    );
  }

  if (mode === 'api' && loading) {
    return (
      <View style={[styles.center, { backgroundColor: colors.paper }]}>
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
    </View>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: Space.xl,
  },
  panel: {
    width: '100%',
    maxWidth: 520,
  },
});
