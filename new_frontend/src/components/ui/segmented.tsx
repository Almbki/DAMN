import { useRef } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useInteraction } from '@/components/ui/interaction';
import { Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

type KeyEvent = {
  key?: string;
  preventDefault?: () => void;
  nativeEvent?: { key?: string };
};

/**
 * Material 3 segmented buttons — a connected, outlined row of mutually
 * exclusive choices. Selected state is the secondary container (never the live
 * "now" colour). Renders as one explicit row; pass `scroll` when the options
 * are wide/numerous, because react-native-web `flexWrap` is unreliable.
 *
 * Keyboard: arrow keys move the selection (roving tab index), Home/End jump to
 * the ends. Disabled segments are skipped.
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
  const refs = useRef<(View | null)[]>([]);

  function nextEnabled(from: number, step: 1 | -1): number | null {
    for (let offset = 1; offset <= options.length; offset += 1) {
      const index = (((from + step * offset) % options.length) + options.length) % options.length;
      if (!disabled.includes(index)) return index;
    }
    return null;
  }

  function firstEnabled(): number | null {
    const index = options.findIndex((_, i) => !disabled.includes(i));
    return index < 0 ? null : index;
  }

  function lastEnabled(): number | null {
    for (let index = options.length - 1; index >= 0; index -= 1) {
      if (!disabled.includes(index)) return index;
    }
    return null;
  }

  function focusSegment(index: number) {
    setTimeout(() => {
      const node = refs.current[index];
      (node as unknown as { focus?: () => void } | null)?.focus?.();
    }, 0);
  }

  function onKeyDown(index: number, event: KeyEvent) {
    const key = event.nativeEvent?.key ?? event.key;
    if (!key) return;

    let next: number | null = null;
    if (key === 'ArrowRight' || key === 'ArrowDown') next = nextEnabled(index, 1);
    else if (key === 'ArrowLeft' || key === 'ArrowUp') next = nextEnabled(index, -1);
    else if (key === 'Home') next = firstEnabled();
    else if (key === 'End') next = lastEnabled();

    if (next == null) return;
    event.preventDefault?.();
    onChange(next);
    focusSegment(next);
  }

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
          <Segment
            key={option}
            refCallback={(node) => {
              refs.current[index] = node;
            }}
            option={option}
            index={index}
            selected={selected}
            off={off}
            size={size}
            tabIndex={selected && !off ? 0 : -1}
            onPress={() => onChange(index)}
            onKeyDown={Platform.OS === 'web' ? (event) => onKeyDown(index, event) : undefined}
          />
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

function Segment({
  option,
  index,
  selected,
  off,
  size,
  tabIndex,
  onPress,
  onKeyDown,
  refCallback,
}: {
  option: string;
  index: number;
  selected: boolean;
  off: boolean;
  size: 'sm' | 'md';
  tabIndex: 0 | -1;
  onPress: () => void;
  onKeyDown?: (event: KeyEvent) => void;
  refCallback: (node: View | null) => void;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();

  return (
    <Pressable
      ref={refCallback}
      accessibilityRole="radio"
      accessibilityState={{ selected, disabled: off }}
      accessibilityLabel={option}
      disabled={off}
      focusable={!off}
      tabIndex={tabIndex}
      onPress={onPress}
      {...(onKeyDown ? ({ onKeyDown } as Record<string, unknown>) : {})}
      {...handlers}
      style={[
        styles.segment,
        index > 0 && { borderLeftWidth: 1, borderLeftColor: colors.outline },
        selected && { backgroundColor: colors.secondaryContainer },
        hovered && !selected && !off && { backgroundColor: colors.hover },
        focused && { boxShadow: `inset 0 0 0 2px ${colors.focusRing}` },
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
    minHeight: 44,
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
