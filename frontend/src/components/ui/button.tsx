import { Pressable, StyleSheet, Text, type StyleProp, type ViewStyle } from 'react-native';

import { Surface } from '@/components/surface';
import { useInteraction } from '@/components/ui/interaction';
import { useRipple } from '@/components/ui/ripple';
import { PressScale, Radius, Space, Type } from '@/constants/tokens';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { useTheme } from '@/state/theme';

type Variant = 'primary' | 'secondary' | 'ghost';

type ButtonProps = {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
};

/** Primary is the accent; nothing else may be. */
export function Button({
  label,
  onPress,
  variant = 'secondary',
  disabled = false,
  style,
}: ButtonProps) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const { focused, hovered, handlers } = useInteraction();

  const isPrimary = variant === 'primary';
  const isGhost = variant === 'ghost';

  const textColor = isPrimary ? colors.onAccent : isGhost ? colors.inkMuted : colors.ink;
  // A ripple reads against the fill it sits on: light on accent, ink elsewhere.
  const ripple = useRipple(isPrimary ? colors.rippleOnAccent : colors.ripple);

  return (
    <Surface
      elevation={isGhost ? 'flat' : 'raised'}
      radius={Radius.sm}
      hairline={variant === 'secondary'}
      background={isPrimary ? colors.accent : isGhost ? undefined : colors.raised}
      ring={focused}
      style={[styles.wrapper, disabled ? styles.disabled : null, style]}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        accessibilityState={{ disabled }}
        disabled={disabled}
        onPress={onPress}
        focusable={!disabled}
        {...handlers}
        onLayout={ripple.onLayout}
        onPressIn={ripple.onPressIn}
        style={({ pressed }) => [
          styles.base,
          {
            backgroundColor:
              pressed && !isPrimary
                ? colors.pressed
                : hovered && !isPrimary
                  ? colors.hover
                  : 'transparent',
            transform: pressed && !reduced ? [{ scale: PressScale }] : undefined,
          },
        ]}>
        {ripple.node}
        <Text style={[styles.label, { color: textColor }]}>{label}</Text>
      </Pressable>
    </Surface>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignSelf: 'flex-start',
  },
  disabled: {
    opacity: 0.38,
  },
  base: {
    minHeight: 44,
    paddingHorizontal: Space.xl,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  label: {
    fontSize: Type.body,
    fontWeight: '500',
  },
});
