import { Pressable, StyleSheet, View } from 'react-native';

import { Icon } from '@/components/ui/icon';
import { Radius } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/**
 * Material 3 checkbox with a 44px touch target. Filled primary when checked,
 * outline when not. The live "now" colour is never used here.
 */
export function Checkbox({
  checked,
  onPress,
  label,
  disabled = false,
}: {
  checked: boolean;
  onPress: () => void;
  label: string;
  disabled?: boolean;
}) {
  const { colors } = useTheme();
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{ checked, disabled }}
      accessibilityLabel={label}
      disabled={disabled}
      onPress={onPress}
      hitSlop={10}
      style={styles.hit}>
      <View
        style={[
          styles.box,
          {
            borderColor: checked ? colors.primary : colors.outline,
            backgroundColor: checked ? colors.primary : 'transparent',
            opacity: disabled ? 0.38 : 1,
          },
        ]}>
        {checked ? <Icon name="check" size={14} color={colors.onPrimary} strokeWidth={2.4} /> : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  hit: {
    width: 28,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  box: {
    width: 20,
    height: 20,
    borderRadius: Radius.xs,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
