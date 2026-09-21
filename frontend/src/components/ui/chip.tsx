import { Pressable, StyleSheet, Text } from 'react-native';

import { Icon, type IconName } from '@/components/ui/icon';
import { useInteraction } from '@/components/ui/interaction';
import { Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/** Material 3 filter chip. Selected = secondary container + check mark. */
export function FilterChip({
  label,
  selected = false,
  onPress,
  icon,
  disabled = false,
  count,
}: {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  icon?: IconName;
  disabled?: boolean;
  count?: number;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const fg = selected ? colors.onSecondaryContainer : colors.ink;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected, disabled }}
      accessibilityLabel={label}
      disabled={disabled}
      onPress={onPress}
      focusable={!disabled}
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
          opacity: disabled ? 0.38 : 1,
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      {selected ? <Icon name="check" size={14} color={fg} strokeWidth={2.4} /> : icon ? <Icon name={icon} size={15} color={fg} /> : null}
      <Text style={[styles.label, { color: fg }]}>{label}</Text>
      {count != null && count > 0 ? (
        <Text style={[styles.count, { color: fg }]}>{count}</Text>
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
    minHeight: 36,
  },
  label: {
    fontSize: Type.labelLarge,
  },
  count: {
    fontFamily: 'IBMPlexMono_400Regular',
    fontSize: Type.labelMedium,
  },
});
