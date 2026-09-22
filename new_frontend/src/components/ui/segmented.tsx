import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/**
 * Material 3 segmented buttons — a connected, outlined row of mutually
 * exclusive choices. Selected state is the secondary container (never the live
 * "now" colour). Renders as one explicit row; pass `scroll` when the options
 * are wide/numerous, because react-native-web `flexWrap` is unreliable.
 */
export function Segmented({
  label,
  options,
  value,
  onChange,
  disabled = [],
  scroll = false,
  size = 'md',
}: {
  label?: string;
  options: readonly string[];
  value: number;
  onChange: (index: number) => void;
  /** Indices that render dimmed and are not selectable. */
  disabled?: number[];
  scroll?: boolean;
  size?: 'sm' | 'md';
}) {
  const { colors } = useTheme();

  const row = (
    <View
      accessibilityRole="radiogroup"
      style={[
        styles.row,
        { borderColor: colors.outline, backgroundColor: colors.surfaceContainerLowest },
      ]}>
      {options.map((option, index) => {
        const selected = index === value;
        const off = disabled.includes(index);
        return (
          <Pressable
            key={option}
            accessibilityRole="radio"
            accessibilityState={{ selected, disabled: off }}
            accessibilityLabel={option}
            disabled={off}
            onPress={() => onChange(index)}
            style={[
              styles.segment,
              index > 0 && { borderLeftWidth: 1, borderLeftColor: colors.outline },
              selected && { backgroundColor: colors.secondaryContainer },
              off && styles.off,
            ]}>
            <Text
              numberOfLines={1}
              style={[
                styles.label,
                size === 'sm' && styles.labelSm,
                { color: selected ? colors.onSecondaryContainer : colors.ink },
                selected && styles.labelSelected,
              ]}>
              {option}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );

  return (
    <View style={styles.wrap}>
      {label ? <Text style={[styles.fieldLabel, { color: colors.inkMuted }]}>{label}</Text> : null}
      {scroll ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.scrollRow}>
          {row}
        </ScrollView>
      ) : (
        row
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: Space.sm,
  },
  fieldLabel: {
    fontSize: Type.labelMedium,
  },
  row: {
    flexDirection: 'row',
    borderWidth: 1,
    borderRadius: Radius.pill,
    overflow: 'hidden',
  },
  scrollRow: {
    flexDirection: 'row',
    paddingVertical: 1,
  },
  segment: {
    flex: 1,
    minHeight: 40,
    paddingHorizontal: Space.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  off: {
    opacity: 0.38,
  },
  label: {
    fontSize: Type.labelLarge,
  },
  labelSm: {
    fontSize: Type.labelMedium,
  },
  labelSelected: {
    fontWeight: '600',
  },
});
