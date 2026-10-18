import { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  type AccessibilityActionEvent,
} from 'react-native';

import { Fonts, Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

const STEPS = 10;

function clampValue(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(STEPS, Math.max(0, Math.round(value)));
}

/**
 * A 0–10 instrument slider. The 11 ticks keep the current value readable even
 * on a narrow card; the whole 44px-high row is the touch target, so a tap sets
 * a value and dragging slides it. Accessibility exposes it as adjustable with
 * increment / decrement actions.
 */
export function ScaleSlider({
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
  const safe = clampValue(value);
  const [trackWidth, setTrackWidth] = useState(0);

  function setFromPosition(x: number) {
    if (trackWidth <= 0) return;
    const ratio = Math.min(1, Math.max(0, x / trackWidth));
    const next = Math.round(ratio * STEPS);
    if (next !== safe) onChange(next);
  }

  function step(delta: number) {
    const next = clampValue(safe + delta);
    if (next !== safe) onChange(next);
  }

  function handleAccessibilityAction(event: AccessibilityActionEvent) {
    if (event.nativeEvent.actionName === 'increment') step(1);
    if (event.nativeEvent.actionName === 'decrement') step(-1);
  }

  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <Text style={[styles.label, { color: colors.inkMuted }]}>{label}</Text>
        <Text style={[styles.value, { color: colors.ink }]}>
          {safe}
          <Text style={[styles.valueUnit, { color: colors.inkFaint }]}> / 10</Text>
        </Text>
      </View>

      <View
        accessible
        accessibilityRole="adjustable"
        accessibilityLabel={label}
        accessibilityValue={{ min: 0, max: STEPS, now: safe, text: `${safe} / ${STEPS}` }}
        accessibilityActions={[
          { name: 'increment', label: '增加' },
          { name: 'decrement', label: '减少' },
        ]}
        onAccessibilityAction={handleAccessibilityAction}
        onLayout={(event) => setTrackWidth(event.nativeEvent.layout.width)}
        onStartShouldSetResponder={() => true}
        onMoveShouldSetResponder={() => true}
        onResponderGrant={(event) => setFromPosition(event.nativeEvent.locationX)}
        onResponderMove={(event) => setFromPosition(event.nativeEvent.locationX)}
        onResponderTerminationRequest={() => false}
        style={styles.touch}>
        <View pointerEvents="none" style={styles.track}>
          {Array.from({ length: STEPS + 1 }, (_, index) => {
            const active = index <= safe;
            const current = index === safe;
            return (
              <View key={index} style={styles.tickColumn}>
                <View
                  style={[
                    styles.tick,
                    {
                      height: current ? 26 : active ? 16 : 10,
                      backgroundColor: active ? colors.primary : colors.outlineVariant,
                      opacity: active ? 1 : 0.85,
                    },
                  ]}
                />
              </View>
            );
          })}
        </View>
      </View>

      <View style={styles.hints}>
        <Text style={[styles.hint, { color: colors.inkFaint }]}>0 · {lowHint}</Text>
        <Text style={[styles.hint, { color: colors.inkFaint }]}>10 · {highHint}</Text>
      </View>
    </View>
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
  valueUnit: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  touch: {
    height: 44,
    justifyContent: 'center',
    borderRadius: Radius.sm,
  },
  track: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 44,
    gap: 3,
  },
  tickColumn: {
    flex: 1,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tick: {
    width: '100%',
    maxWidth: 8,
    borderRadius: 4,
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
