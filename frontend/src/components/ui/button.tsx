import { Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import { useInteraction } from '@/components/ui/interaction';
import { Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

type Variant = 'primary' | 'secondary' | 'ghost';

type ButtonProps = {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
};

export function Button({
  label,
  onPress,
  variant = 'secondary',
  disabled = false,
  style,
}: ButtonProps) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();

  const isPrimary = variant === 'primary';
  const isSecondary = variant === 'secondary';

  const restBackground = isPrimary ? colors.ink : 'transparent';
  const textColor = isPrimary ? colors.onInk : variant === 'ghost' ? colors.inkMuted : colors.ink;

  return (
    <View style={[styles.wrapper, style]}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        disabled={disabled}
        onPress={onPress}
        focusable={!disabled}
        {...handlers}
        style={({ pressed }) => [
          styles.base,
          {
            backgroundColor: pressed
              ? isPrimary
                ? colors.ink
                : colors.pressed
              : hovered && !isPrimary
                ? colors.hover
                : restBackground,
            borderColor: isSecondary ? colors.lineStrong : 'transparent',
            borderWidth: isSecondary ? 1 : 0,
            opacity: disabled ? 0.38 : pressed && isPrimary ? 0.9 : 1,
            boxShadow: focused ? `0 0 0 2px ${colors.lineStrong}` : undefined,
          },
        ]}>
        <Text style={[styles.label, { color: textColor }]}>{label}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignSelf: 'flex-start',
  },
  base: {
    minHeight: 44,
    paddingHorizontal: Space.xl,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  label: {
    fontSize: Type.body,
    fontWeight: '500',
  },
});
