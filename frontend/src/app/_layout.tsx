import { IBMPlexMono_400Regular } from '@expo-google-fonts/ibm-plex-mono/400Regular';
import { IBMPlexMono_500Medium } from '@expo-google-fonts/ibm-plex-mono/500Medium';
import { IBMPlexMono_600SemiBold } from '@expo-google-fonts/ibm-plex-mono/600SemiBold';
import { useFonts } from 'expo-font';
import { Slot } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View } from 'react-native';

import { AppShell } from '@/components/shell/app-shell';
import { PlanProvider } from '@/state/plan';
import { PreferencesProvider } from '@/state/preferences';
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
      <PreferencesProvider>
        <PlanProvider>
          <RootShell />
        </PlanProvider>
      </PreferencesProvider>
    </ThemeProvider>
  );
}

function RootShell() {
  const { colors, resolved } = useTheme();
  return (
    <View style={{ flex: 1, backgroundColor: colors.paper }}>
      <StatusBar style={resolved === 'dark' ? 'light' : 'dark'} />
      <AppShell>
        <Slot />
      </AppShell>
    </View>
  );
}
