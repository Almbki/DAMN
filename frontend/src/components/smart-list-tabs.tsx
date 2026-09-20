import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { Radius, Space, Type } from '@/constants/tokens';
import type { SmartListKey } from '@/state/plan';
import { useTheme } from '@/state/theme';

const ITEMS: { key: SmartListKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'today', label: '今天' },
  { key: 'tomorrow', label: '明天' },
  { key: 'upcoming', label: '即将到来' },
  { key: 'overdue', label: '已逾期' },
  { key: 'noDate', label: '无日期' },
];

/**
 * Horizontal filter chips in a ScrollView. Deliberately not a wrapping flex row:
 * `flexWrap` is unreliable in react-native-web (see AGENTS.md).
 */
export function SmartListTabs({
  value,
  counts,
  onChange,
}: {
  value: SmartListKey;
  counts: Record<SmartListKey, number>;
  onChange: (key: SmartListKey) => void;
}) {
  const { colors } = useTheme();
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.row}>
      {ITEMS.map((item) => {
        const selected = item.key === value;
        const count = counts[item.key];
        return (
          <Pressable
            key={item.key}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            accessibilityLabel={item.label}
            onPress={() => onChange(item.key)}
            style={[
              styles.chip,
              {
                borderColor: selected ? colors.ink : colors.line,
                backgroundColor: selected ? colors.ink : 'transparent',
              },
            ]}>
            <Text style={[styles.label, { color: selected ? colors.onInk : colors.ink }]}>
              {item.label}
            </Text>
            {count > 0 ? (
              <Text style={[styles.count, { color: selected ? colors.onInk : colors.inkMuted }]}>
                {count}
              </Text>
            ) : null}
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: Space.sm,
    paddingVertical: Space.xs,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.md,
    minHeight: 36,
  },
  label: {
    fontSize: Type.small,
  },
  count: {
    fontSize: Type.micro,
    fontFamily: 'IBMPlexMono_400Regular',
  },
});
