import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Line, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/** Shared centered layout for the unauthenticated Login/Register screens. */
export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.paper }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={[
          styles.scroll,
          {
            paddingTop: insets.top + Space.xxxl,
            paddingBottom: insets.bottom + Space.xxl,
            paddingLeft: Math.max(Space.xl, insets.left + Space.xl),
            paddingRight: Math.max(Space.xl, insets.right + Space.xl),
          },
        ]}>
        <View style={styles.panel}>
          <Text style={[styles.brand, { color: colors.inkFaint }]}>DAMN · 任务清单智能体</Text>
          <Text accessibilityRole="header" style={[styles.title, { color: colors.ink }]}>
            {title}
          </Text>
          <Text style={[styles.subtitle, { color: colors.inkMuted }]}>{subtitle}</Text>
          {children}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  scroll: { flexGrow: 1, alignItems: 'center', justifyContent: 'center' },
  panel: { width: '100%', maxWidth: 460, gap: Space.md },
  brand: { fontSize: Type.labelMedium, letterSpacing: 0.6 },
  title: {
    fontSize: Type.heading,
    lineHeight: Type.heading * Line.normal,
    fontWeight: '600',
  },
  subtitle: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
  },
});