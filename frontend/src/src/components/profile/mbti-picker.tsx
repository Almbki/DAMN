import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useInteraction } from '@/components/ui/interaction';
import { Fonts, Radius, Type } from '@/constants/tokens';
import { GRID_COLUMNS, MBTI_TYPES, chunk, type MbtiType } from '@/domain/mbti';
import { useTheme } from '@/state/theme';

/**
 * 16-type single-select, laid out as an explicit 4×4 grid of hairline cells.
 * Rows are built in JS because react-native-web `flexWrap` is unreliable.
 * Selected cell uses the live mint accent; unselected cells stay neutral.
 */
export function MbtiPicker({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (type: MbtiType) => void;
}) {
  const { colors } = useTheme();
  const rows = chunk(MBTI_TYPES, GRID_COLUMNS);

  return (
    <View
      accessibilityRole="radiogroup"
      accessibilityLabel="MBTI 类型"
      style={[styles.grid, { borderColor: colors.line, backgroundColor: colors.surfaceContainerLowest }]}>
      {rows.map((row) => (
        <View key={row[0]} style={styles.row}>
          {row.map((type) => (
            <MbtiCell
              key={type}
              type={type}
              selected={value === type}
              onPress={() => onChange(type)}
            />
          ))}
        </View>
      ))}
    </View>
  );
}

function MbtiCell({
  type,
  selected,
  onPress,
}: {
  type: MbtiType;
  selected: boolean;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();

  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      accessibilityLabel={type}
      onPress={onPress}
      {...handlers}
      style={[
        styles.cell,
        {
          borderColor: colors.line,
          backgroundColor: selected
            ? colors.nowContainer
            : hovered
              ? colors.hover
              : colors.surfaceContainerLowest,
          boxShadow: focused ? `inset 0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      <Text
        style={[
          styles.code,
          { color: selected ? colors.onNow : colors.ink },
          selected && styles.codeSelected,
        ]}>
        {type}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  grid: {
    borderTopWidth: 1,
    borderLeftWidth: 1,
    borderRadius: Radius.sm,
    overflow: 'hidden',
    maxWidth: 440,
  },
  row: {
    flexDirection: 'row',
  },
  cell: {
    flex: 1,
    minHeight: 52,
    alignItems: 'center',
    justifyContent: 'center',
    borderRightWidth: 1,
    borderBottomWidth: 1,
  },
  code: {
    fontFamily: Fonts.mono,
    fontSize: Type.titleSmall,
    letterSpacing: 1,
  },
  codeSelected: {
    fontWeight: '600',
  },
});
