import { Pressable, StyleSheet, View } from 'react-native';

import { useInteraction } from '@/components/ui/interaction';
import { Radius } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/** A visible 44px overflow affordance — never hidden behind hover. */
export function DotsButton({
  label,
  onPress,
  disabled = false,
}: {
  label: string;
  onPress: () => void;
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
      {...handlers}
      style={[
        styles.button,
        {
          backgroundColor: hovered && !disabled ? colors.hover : 'transparent',
          opacity: disabled ? 0.38 : 1,
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      <View style={styles.dots} pointerEvents="none">
        {[0, 1, 2].map((index) => (
          <View key={index} style={[styles.dot, { backgroundColor: colors.inkMuted }]} />
        ))}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    width: 44,
    height: 44,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dots: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  dot: {
    width: 4,
    height: 4,
    borderRadius: 2,
  },
});
