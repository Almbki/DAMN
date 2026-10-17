import { Pressable, StyleSheet, Text } from 'react-native';

import { Icon, type IconName } from '@/components/ui/icon';
import { useInteraction } from '@/components/ui/interaction';
import { Fonts, Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/** Filter chip with a full 44px touch target (the shared chip is 36px). */
export function TaskFilterChip({
  label,
  selected = false,
  onPress,
  icon,
  count,
}: {
  label: string;
  selected?: boolean;
  onPress: () => void;
  icon?: IconName;
  count?: number;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const foreground = selected ? colors.onSecondaryContainer : colors.ink;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      accessibilityLabel={label}
      onPress={onPress}
      {...handlers}
      style={[
        styles.chip,
        {
          borderColor: selected ? 'transparent' : colors.outline,
          backgroundColor: selected
            ? colors.secondaryContainer
            : hovered
              ? colors.hover
              : 'transparent',
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      {selected ? (
        <Icon name="check" size={14} color={foreground} strokeWidth={2.4} />
      ) : icon ? (
        <Icon name={icon} size={15} color={foreground} />
      ) : null}
      <Text numberOfLines={1} style={[styles.label, { color: foreground }]}>
        {label}
      </Text>
      {count != null && count > 0 ? (
        <Text numberOfLines={1} style={[styles.count, { color: foreground }]}>
          {count}
        </Text>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
    borderWidth: 1,
    borderRadius: Radius.pill,
    paddingHorizontal: Space.lg,
    minHeight: 44,
  },
  label: {
    fontSize: Type.labelLarge,
  },
  count: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
});
