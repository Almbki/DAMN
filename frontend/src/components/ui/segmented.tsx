import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Radius, Space, Type } from '@/constants/tokens';import { useTheme } from '@/state/theme';

/**
 * A row of mutually exclusive choices. Selected state is a filled ink chip — the
 * mint accent is reserved for "now", so selection never borrows it.
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
        {options.map((option, index) => {
          const selected = index === value;
          return (
            <Pressable
              key={option}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              accessibilityLabel={option}
              onPress={() => onChange(index)}
              style={[
                styles.chip,
                {
                  borderColor: selected ? colors.ink : colors.line,
                  backgroundColor: selected ? colors.ink : 'transparent',
                },
              ]}>
              <Text style={[styles.chipText, { color: selected ? colors.onInk : colors.ink }]}>
                {option}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
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
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  chip: {
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.lg,
    minHeight: 40,
    justifyContent: 'center',
  },
  chipText: {
    fontSize: Type.body,
  },
});
