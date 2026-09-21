import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Surface } from '@/components/surface';
import { useInteraction } from '@/components/ui/interaction';
import { useRipple } from '@/components/ui/ripple';
import { PressScale, Radius, Space, Type } from '@/constants/tokens';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { useTheme } from '@/state/theme';

/**
 * A row of mutually exclusive choices, split evenly — never wrapped (react-
 * native-web eats `flexWrap`). The selected choice is an inset, recessed
 * surface; the accent is reserved for "now", so selection never borrows it.
 */
export function Segmented({
  label,
  options,
  value,
  onChange,
}: {
  label?: string;
  options: readonly string[];
  value: number;
  onChange: (index: number) => void;
}) {
  const { colors } = useTheme();

  return (
    <View style={styles.wrap}>
      {label ? <Text style={[styles.label, { color: colors.inkMuted }]}>{label}</Text> : null}
      <View style={styles.row}>
        {options.map((option, index) => (
          <Segment
            key={option}
            label={option}
            selected={index === value}
            onPress={() => onChange(index)}
          />
        ))}
      </View>
    </View>
  );
}

function Segment({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const { focused, hovered, handlers } = useInteraction();
  const ripple = useRipple(colors.ripple);

  return (
    <Surface
      elevation={selected ? 'inset' : 'flat'}
      radius={Radius.sm}
      ring={focused}
      style={styles.cell}>
      <Pressable
        accessibilityRole="radio"
        accessibilityState={{ selected }}
        accessibilityLabel={label}
        onPress={onPress}
        {...handlers}
        onLayout={ripple.onLayout}
        onPressIn={ripple.onPressIn}
        style={({ pressed }) => [
          styles.press,
          {
            backgroundColor: pressed
              ? colors.pressed
              : hovered && !selected
                ? colors.hover
                : 'transparent',
            transform: pressed && !reduced ? [{ scale: PressScale }] : undefined,
          },
        ]}>
        {ripple.node}
        <Text
          numberOfLines={1}
          style={[
            styles.text,
            { color: selected ? colors.ink : colors.inkMuted, fontWeight: selected ? '700' : '400' },
          ]}>
          {label}
        </Text>
      </Pressable>
    </Surface>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: Space.sm,
  },
  label: {
    fontSize: Type.small,
  },
  row: {
    flexDirection: 'row',
    gap: Space.sm,
  },
  cell: {
    flex: 1,
  },
  press: {
    minHeight: 44,
    paddingHorizontal: Space.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    fontSize: Type.body,
  },
});
