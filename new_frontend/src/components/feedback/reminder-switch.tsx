import { Pressable, StyleSheet, View } from 'react-native';

import { useInteraction } from '@/components/ui/interaction';
import { Radius } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/** A 44px-tall pill switch that matches the paper/ink surfaces. */
export function ReminderSwitch({
  value,
  onValueChange,
  label,
  disabled = false,
}: {
  value: boolean;
  onValueChange: (next: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();

  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityLabel={label}
      accessibilityState={{ checked: value, disabled }}
      disabled={disabled}
      onPress={() => onValueChange(!value)}
      {...handlers}
      style={[
        styles.touch,
        {
          opacity: disabled ? 0.5 : 1,
          backgroundColor: hovered && !disabled ? colors.hover : 'transparent',
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      <View
        style={[
          styles.track,
          {
            backgroundColor: value ? colors.primary : colors.surfaceContainerHighest,
            borderColor: value ? colors.primary : colors.outline,
          },
        ]}>
        <View
          style={[
            styles.knob,
            {
              backgroundColor: value ? colors.onPrimary : colors.surfaceContainerLowest,
              transform: [{ translateX: value ? 20 : 0 }],
            },
          ]}
        />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  touch: {
    width: 56,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: Radius.pill,
  },
  track: {
    width: 48,
    height: 28,
    borderRadius: Radius.pill,
    borderWidth: 1,
    padding: 2,
    justifyContent: 'center',
  },
  knob: {
    width: 22,
    height: 22,
    borderRadius: 11,
    shadowColor: '#1A2820',
    shadowOpacity: 0.14,
    shadowRadius: 2,
    shadowOffset: { width: 0, height: 1 },
    elevation: 1,
  },
});
