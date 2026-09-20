import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { Line, Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/**
 * Empty and error are moments for direction, not mood: say what happened and
 * what to do next, once. Loading is honest — no fake staged progress.
 */

export function EmptyState({
  title,
  body,
  actionLabel,
  onAction,
}: {
  title: string;
  body: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  const { colors } = useTheme();
  return (
    <View style={[styles.box, styles.dashed, { borderColor: colors.line }]}>
      <Text style={[styles.title, { color: colors.ink }]}>{title}</Text>
      <Text style={[styles.body, { color: colors.inkMuted }]}>{body}</Text>
      {actionLabel && onAction ? <Button label={actionLabel} onPress={onAction} /> : null}
    </View>
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
    <View style={[styles.box, { borderColor: colors.line }]}>
      <Text style={[styles.title, { color: colors.ink }]}>{title}</Text>
      <Text style={[styles.body, { color: colors.inkMuted }]}>{body}</Text>
      {onRetry ? <Button label="重试" variant="secondary" onPress={onRetry} /> : null}
    </View>
  );
}

export function LoadingState({ label }: { label: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.loading}>
      <ActivityIndicator color={colors.inkMuted} />
      <Text style={[styles.body, { color: colors.inkMuted }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: Space.xl,
    gap: Space.md,
  },
  dashed: {
    borderStyle: 'dashed',
  },
  title: {
    fontSize: Type.title,
    fontWeight: '700',
  },
  body: {
    fontSize: Type.body,
    lineHeight: Type.body * Line.normal,
    maxWidth: 560,
  },
  loading: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    paddingVertical: Space.xl,
  },
});
