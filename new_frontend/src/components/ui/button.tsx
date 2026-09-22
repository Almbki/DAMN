import { Pressable, StyleSheet, Text, type StyleProp, type ViewStyle, View } from 'react-native';

import { Icon, type IconName } from '@/components/ui/icon';
import { useInteraction } from '@/components/ui/interaction';
import { shadowFor } from '@/components/ui/surface';
import { Elevation, Radius, Space, StateLayer, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/**
 * Material 3 button. Variants: filled / tonal / outlined / text.
 * Every variant is a pill with a 44px touch target; the state layer is a real
 * overlay so the press reads as the surface going in (`Elevation.inset`).
 */
export type ButtonVariant = 'filled' | 'tonal' | 'outlined' | 'text';

const ALIASES: Record<string, ButtonVariant> = {
  primary: 'filled',
  secondary: 'outlined',
  ghost: 'text',
};

type ButtonProps = {
  label: string;
  onPress?: () => void;
  variant?: ButtonVariant | 'primary' | 'secondary' | 'ghost';
  icon?: IconName;
  disabled?: boolean;
  size?: 'sm' | 'md';
  style?: StyleProp<ViewStyle>;
};

export function Button({
  label,
  onPress,
  variant = 'tonal',
  icon,
  disabled = false,
  size = 'md',
  style,
}: ButtonProps) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const kind = ALIASES[variant] ?? (variant as ButtonVariant);

  const background =
    kind === 'filled'
      ? colors.primary
      : kind === 'tonal'
        ? colors.primaryContainer
        : 'transparent';
  const borderColor = kind === 'outlined' ? colors.outline : 'transparent';
  const textColor =
    kind === 'filled'
      ? colors.onPrimary
      : kind === 'tonal'
        ? colors.onPrimaryContainer
        : colors.primary;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      focusable={!disabled}
      {...handlers}
      style={({ pressed }) => [
        styles.base,
        size === 'sm' && styles.sm,
        {
          backgroundColor: background,
          borderWidth: kind === 'outlined' ? 1 : 0,
          borderColor,
          opacity: disabled ? 0.38 : 1,
          boxShadow: focused
            ? `0 0 0 2px ${colors.focusRing}, ${shadowFor('level1', false)}`
            : pressed
              ? Elevation.inset
              : shadowFor(kind === 'filled' || kind === 'tonal' ? 'level1' : 'level0', false),
        },
        style,
      ]}>
      {({ pressed }) => (
        <>
          <View
            style={[
              StyleSheet.absoluteFill,
              {
                backgroundColor: stateOverlay(kind, hovered, pressed, colors),
                pointerEvents: 'none',
              },
            ]}
          />
          {icon ? <Icon name={icon} size={size === 'sm' ? 16 : 18} color={textColor} /> : null}
          <Text style={[styles.label, size === 'sm' && styles.labelSm, { color: textColor }]}>
            {label}
          </Text>
        </>
      )}
    </Pressable>
  );
}

function stateOverlay(
  kind: ButtonVariant,
  hovered: boolean,
  pressed: boolean,
  colors: { hover: string; pressed: string },
): string {
  if (!pressed && !hovered) return 'transparent';
  if (kind === 'filled') {
    return `rgba(255,255,255,${pressed ? StateLayer.pressed + 0.04 : StateLayer.hover + 0.02})`;
  }
  return pressed ? colors.pressed : colors.hover;
}

export function IconButton({
  name,
  label,
  onPress,
  disabled = false,
  selected = false,
  size = 44,
  style,
}: {
  name: IconName;
  label: string;
  onPress?: () => void;
  disabled?: boolean;
  selected?: boolean;
  size?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled, selected }}
      disabled={disabled}
      onPress={onPress}
      focusable={!disabled}
      {...handlers}
      style={({ pressed }) => [
        styles.iconBtn,
        {
          width: size,
          height: size,
          backgroundColor: selected
            ? colors.secondaryContainer
            : hovered
              ? colors.hover
              : 'transparent',
          opacity: disabled ? 0.38 : 1,
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
          transform: pressed ? [{ translateY: 1 }] : undefined,
        },
        style,
      ]}>
      <Icon
        name={name}
        size={size > 44 ? 22 : 20}
        color={selected ? colors.onSecondaryContainer : colors.ink}
      />
    </Pressable>
  );
}

/** Material 3 floating action button (round). */
export function Fab({
  icon,
  label,
  onPress,
  disabled = false,
  variant = 'tonal',
}: {
  icon: IconName;
  label: string;
  onPress?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'tonal';
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const bg = variant === 'primary' ? colors.primary : colors.primaryContainer;
  const fg = variant === 'primary' ? colors.onPrimary : colors.onPrimaryContainer;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      focusable={!disabled}
      {...handlers}
      style={[
        styles.fab,
        {
          backgroundColor: bg,
          opacity: disabled ? 0.38 : 1,
          transform: hovered && !disabled ? [{ translateY: -1 }] : undefined,
          boxShadow: focused
            ? `0 0 0 2px ${colors.focusRing}`
            : disabled
              ? undefined
              : Elevation.level3,
        },
      ]}>
      <Icon name={icon} size={24} color={fg} />
    </Pressable>
  );
}

/** Material 3 extended FAB — an icon + a label, for the one named action. */
export function ExtendedFab({
  icon,
  label,
  onPress,
  disabled = false,
}: {
  icon: IconName;
  label: string;
  onPress?: () => void;
  disabled?: boolean;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      focusable={!disabled}
      {...handlers}
      style={[
        styles.extFab,
        {
          backgroundColor: colors.primaryContainer,
          opacity: disabled ? 0.38 : 1,
          transform: hovered && !disabled ? [{ translateY: -1 }] : undefined,
          boxShadow: focused
            ? `0 0 0 2px ${colors.focusRing}`
            : disabled
              ? undefined
              : Elevation.level3,
        },
      ]}>
      <Icon name={icon} size={20} color={colors.onPrimaryContainer} />
      <Text style={[styles.extFabLabel, { color: colors.onPrimaryContainer }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 44,
    paddingHorizontal: Space.xl,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: Space.sm,
    overflow: 'hidden',
  },
  sm: {
    minHeight: 34,
    paddingHorizontal: Space.lg,
  },
  label: {
    fontSize: Type.labelLarge,
    fontWeight: '500',
  },
  labelSm: {
    fontSize: Type.labelMedium,
  },
  iconBtn: {
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fab: {
    width: 56,
    height: 56,
    borderRadius: Radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  extFab: {
    minHeight: 56,
    paddingHorizontal: Space.xl,
    borderRadius: Radius.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  extFabLabel: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
  },
});
