import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { Surface } from '@/components/ui/surface';
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

/**
 * An inline, dismissible message. Unlike `ErrorState` it never replaces the
 * surrounding form — it sits above it so the user can keep working.
 */
export function InlineNotice({
  message,
  tone = 'error',
  actionLabel,
  onAction,
  onDismiss,
}: {
  message: string;
  tone?: 'error' | 'info' | 'success';
  actionLabel?: string;
  onAction?: () => void;
  onDismiss?: () => void;
}) {
  const { colors } = useTheme();
  const palette =
    tone === 'error'
      ? {
          background: colors.errorContainer,
          border: colors.error,
          text: colors.onErrorContainer,
        }
      : tone === 'success'
        ? {
            background: colors.primaryContainer,
            border: colors.primary,
            text: colors.onPrimaryContainer,
          }
        : {
            background: colors.surfaceContainerLow,
            border: colors.outlineVariant,
            text: colors.inkMuted,
          };

  return (
    <View
      accessibilityRole={tone === 'error' ? 'alert' : undefined}
      accessibilityLiveRegion="polite"
      style={[styles.notice, { backgroundColor: palette.background, borderColor: palette.border }]}>
      <Text style={[styles.noticeText, { color: palette.text }]}>{message}</Text>
      {actionLabel && onAction ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={actionLabel}
          onPress={onAction}
          hitSlop={8}
          style={styles.noticeAction}>
          <Text style={[styles.noticeActionText, { color: palette.text }]}>{actionLabel}</Text>
        </Pressable>
      ) : null}
      {onDismiss ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="关闭提示"
          onPress={onDismiss}
          hitSlop={8}
          style={styles.noticeDismiss}>
          <Icon name="close" size={14} color={palette.text} />
        </Pressable>
      ) : null}
    </View>
  );
}

export type SaveState = 'idle' | 'saving' | 'saved' | 'error';

/** The shared "保存中 / 已保存 / 保存失败" status line. */
export function SaveStatus({ state }: { state: SaveState }) {
  const { colors } = useTheme();
  if (state === 'idle') return null;
  const label = state === 'saving' ? '保存中…' : state === 'saved' ? '已保存' : '保存失败';
  return (
    <Text
      accessibilityLiveRegion="polite"
      style={[
        styles.saveStatus,
        { color: state === 'error' ? colors.error : state === 'saved' ? colors.primary : colors.inkMuted },
      ]}>
      {label}
    </Text>
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
  notice: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingVertical: Space.sm,
    paddingHorizontal: Space.md,
  },
  noticeText: {
    flex: 1,
    fontSize: Type.labelLarge,
    lineHeight: Type.labelLarge * Line.normal,
  },
  noticeAction: {
    minHeight: 32,
    justifyContent: 'center',
  },
  noticeActionText: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  noticeDismiss: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  saveStatus: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
});
