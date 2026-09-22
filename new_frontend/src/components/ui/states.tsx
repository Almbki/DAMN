import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { Surface } from '@/components/ui/surface';
import { Line, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/**
 * Empty and error are moments for direction, not mood: say what happened and
 * what to do next, once. Loading is honest — no fake staged progress.
 */

export function EmptyState({
  title,
  body,
  actionLabel,
  actionIcon,
  onAction,
}: {
  title: string;
  body: string;
  actionLabel?: string;
  actionIcon?: Parameters<typeof Button>[0]['icon'];
  onAction?: () => void;
}) {
  const { colors } = useTheme();
  return (
    <Surface level="level0" radius="lg" bordered style={{ borderStyle: 'dashed' }}>
      <View style={styles.box}>
        <Text style={[styles.title, { color: colors.ink }]}>{title}</Text>
        <Text style={[styles.body, { color: colors.inkMuted }]}>{body}</Text>
        {actionLabel && onAction ? (
          <Button label={actionLabel} icon={actionIcon} variant="tonal" onPress={onAction} />
        ) : null}
      </View>
    </Surface>
  );
}

export function ErrorState({
  title,
  body,
  onRetry,
}: {
  title: string;
  body: string;
  onRetry?: () => void;
}) {
  const { colors } = useTheme();
  return (
    <Surface level="level1" radius="lg">
      <View style={styles.box}>
        <Text style={[styles.title, { color: colors.error }]}>{title}</Text>
        <Text style={[styles.body, { color: colors.inkMuted }]}>{body}</Text>
        {onRetry ? <Button label="重试" variant="tonal" onPress={onRetry} /> : null}
      </View>
    </Surface>
  );
}

export function LoadingState({ label }: { label: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.loading}>
      <ActivityIndicator color={colors.primary} />
      <Text style={[styles.body, { color: colors.inkMuted }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    padding: Space.xl,
    gap: Space.md,
  },
  title: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 560,
  },
  loading: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    paddingVertical: Space.xl,
  },
});
