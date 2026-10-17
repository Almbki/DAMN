import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Icon } from '@/components/ui/icon';
import { useInteraction } from '@/components/ui/interaction';
import { Fonts, Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/**
 * 0..10 level input. A big mono number + two 44px steppers and a tick track;
 * this stays legible on a narrow sheet, unlike eleven tiny number chips.
 */
export function LevelStepper({
  label,
  value,
  onChange,
  lowHint = '很低',
  highHint = '很高',
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  lowHint?: string;
  highHint?: string;
}) {
  const { colors } = useTheme();
  const safe = Number.isFinite(value) ? Math.min(10, Math.max(0, Math.round(value))) : 0;

  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <Text style={[styles.label, { color: colors.inkMuted }]}>{label}</Text>
        <Text style={[styles.value, { color: colors.ink }]}>{safe}</Text>
      </View>

      <View style={styles.controlRow}>
        <StepButton
          label={`降低${label}`}
          icon="minus"
          disabled={safe <= 0}
          onPress={() => onChange(Math.max(0, safe - 1))}
        />

        <View style={styles.track} pointerEvents="none" accessibilityElementsHidden>
          {Array.from({ length: 11 }, (_, index) => (
            <View
              key={index}
              style={[
                styles.tick,
                { backgroundColor: index <= safe ? colors.primary : colors.outlineVariant },
              ]}
            />
          ))}
        </View>

        <StepButton
          label={`提高${label}`}
          icon="plus"
          disabled={safe >= 10}
          onPress={() => onChange(Math.min(10, safe + 1))}
        />
      </View>

      <View style={styles.hints}>
        <Text style={[styles.hint, { color: colors.inkFaint }]}>0 · {lowHint}</Text>
        <Text style={[styles.hint, { color: colors.inkFaint }]}>10 · {highHint}</Text>
      </View>
    </View>
  );
}

function StepButton({
  label,
  icon,
  disabled,
  onPress,
}: {
  label: string;
  icon: 'minus' | 'plus';
  disabled: boolean;
  onPress: () => void;
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
        styles.step,
        {
          borderColor: colors.outline,
          backgroundColor: hovered && !disabled ? colors.hover : 'transparent',
          opacity: disabled ? 0.38 : 1,
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      <Icon name={icon} size={16} color={colors.primary} strokeWidth={2.4} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexGrow: 1,
    flexBasis: 220,
    minWidth: 0,
    gap: Space.xs,
  },
  head: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  label: {
    fontSize: Type.labelMedium,
  },
  value: {
    fontFamily: Fonts.mono,
    fontSize: Type.titleLarge,
  },
  controlRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  step: {
    width: 44,
    height: 44,
    borderRadius: Radius.pill,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  track: {
    flex: 1,
    minWidth: 0,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    height: 12,
  },
  tick: {
    flex: 1,
    height: 6,
    borderRadius: 3,
  },
  hints: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  hint: {
    fontSize: Type.labelSmall,
  },
});
