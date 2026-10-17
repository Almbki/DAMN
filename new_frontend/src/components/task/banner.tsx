import { Pressable, StyleSheet, Text, type StyleProp, View, type ViewStyle } from 'react-native';

import { Icon, type IconName } from '@/components/ui/icon';
import { useInteraction } from '@/components/ui/interaction';
import { Line, Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

type Tone = 'info' | 'success' | 'error';

/**
 * Inline, dismissible message strip. Actions deliberately do not reuse the pill
 * Button: on a tinted banner the colored text reads better and keeps a 44px
 * target without the heavy pill shadow.
 */
export function Banner({
  title,
  body,
  tone = 'info',
  icon,
  actionLabel,
  onAction,
  onDismiss,
  style,
}: {
  title?: string;
  body?: string;
  tone?: Tone;
  icon?: IconName;
  actionLabel?: string;
  onAction?: () => void;
  onDismiss?: () => void;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors } = useTheme();
  const palette =
    tone === 'error'
      ? {
          background: colors.errorContainer,
          border: colors.error,
          foreground: colors.onErrorContainer,
        }
      : tone === 'success'
        ? {
            background: colors.primaryContainer,
            border: colors.primary,
            foreground: colors.onPrimaryContainer,
          }
        : {
            background: colors.surfaceContainerLow,
            border: colors.outlineVariant,
            foreground: colors.ink,
          };

  return (
    <View
      accessibilityLiveRegion="polite"
      style={[
        styles.banner,
        { backgroundColor: palette.background, borderColor: palette.border },
        style,
      ]}>
      <View style={styles.main}>
        {icon ? <Icon name={icon} size={18} color={palette.foreground} /> : null}
        <View style={styles.copy}>
          {title ? (
            <Text style={[styles.title, { color: palette.foreground }]}>{title}</Text>
          ) : null}
          {body ? (
            <Text style={[styles.body, { color: palette.foreground }]}>{body}</Text>
          ) : null}
        </View>
      </View>

      <View style={styles.actions}>
        {actionLabel && onAction ? (
          <BannerAction label={actionLabel} color={palette.foreground} onPress={onAction} />
        ) : null}
        {onDismiss ? <DismissButton label="关闭提示" color={palette.foreground} onPress={onDismiss} /> : null}
      </View>
    </View>
  );
}

function BannerAction({
  label,
  color,
  onPress,
}: {
  label: string;
  color: string;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      {...handlers}
      style={[
        styles.action,
        {
          backgroundColor: hovered ? colors.hover : 'transparent',
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      <Text style={[styles.actionText, { color }]}>{label}</Text>
    </Pressable>
  );
}

function DismissButton({
  label,
  color,
  onPress,
}: {
  label: string;
  color: string;
  onPress: () => void;
}) {
  const { focused, hovered, handlers } = useInteraction();
  const { colors } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      {...handlers}
      style={[
        styles.dismiss,
        {
          backgroundColor: hovered ? colors.hover : 'transparent',
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      <Icon name="close" size={16} color={color} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  banner: {
    borderWidth: 1,
    borderRadius: Radius.lg,
    paddingLeft: Space.md,
    paddingRight: Space.xs,
    paddingVertical: Space.sm,
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: Space.sm,
  },
  main: {
    flex: 1,
    minWidth: 200,
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Space.sm,
    paddingVertical: Space.xs,
  },
  copy: {
    flex: 1,
    gap: 2,
  },
  title: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
    lineHeight: Type.labelLarge * Line.normal,
  },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  action: {
    minHeight: 44,
    paddingHorizontal: Space.md,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: Radius.pill,
  },
  actionText: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
  },
  dismiss: {
    width: 44,
    height: 44,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
