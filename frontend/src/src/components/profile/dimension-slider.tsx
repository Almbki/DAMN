import { useCallback, useRef, useState } from 'react';
import { StyleSheet, Text, View, type GestureResponderEvent, type LayoutChangeEvent } from 'react-native';

import { Fonts, Radius, Space, Type } from '@/constants/tokens';
import { DIMENSION_LETTERS, clamp01, type MbtiDimension } from '@/domain/mbti';
import { useTheme } from '@/state/theme';

const THUMB = 18;
const TRACK_HEIGHT = THUMB + 10;
const FILL_HEIGHT = 4;

/**
 * One MBTI axis as a tap/drag track. `value` is `0..1` toward the FIRST letter
 * (I / S / T / J). Built on the RN responder system so a mouse works on
 * react-native-web and a finger works on native — no gesture library, no
 * `flexWrap`. Screen readers get `adjustable` increment/decrement actions.
 */
export function DimensionSlider({
  dimension,
  value,
  onChange,
}: {
  dimension: MbtiDimension;
  value: number;
  onChange: (weight: number) => void;
}) {
  const { colors } = useTheme();
  const [first, second] = DIMENSION_LETTERS[dimension];
  const widthRef = useRef(0);
  const [trackWidth, setTrackWidth] = useState(0);

  const setFromX = useCallback(
    (x: number) => {
      const travel = Math.max(1, widthRef.current - THUMB);
      onChange(clamp01((x - THUMB / 2) / travel));
    },
    [onChange],
  );

  const onLayout = useCallback((event: LayoutChangeEvent) => {
    const width = event.nativeEvent.layout.width;
    widthRef.current = width;
    setTrackWidth(width);
  }, []);

  const onPointer = useCallback(
    (event: GestureResponderEvent) => setFromX(event.nativeEvent.locationX),
    [setFromX],
  );

  const ratio = clamp01(value);
  const firstPercent = Math.round(ratio * 100);
  const secondPercent = 100 - firstPercent;
  const travel = Math.max(0, trackWidth - THUMB);

  return (
    <View style={styles.wrap}>
      <View style={styles.labels}>
        <View style={styles.labelGroup}>
          <Text style={[styles.letter, { color: colors.ink }]}>{first}</Text>
          <Text style={[styles.percent, { color: colors.ink }]}>{firstPercent}%</Text>
        </View>
        <View style={styles.labelGroup}>
          <Text style={[styles.percent, { color: colors.inkFaint }]}>{secondPercent}%</Text>
          <Text style={[styles.letter, { color: colors.ink }]}>{second}</Text>
        </View>
      </View>

      <View
        accessibilityRole="adjustable"
        accessibilityLabel={`${first} 到 ${second}`}
        accessibilityValue={{ min: 0, max: 100, now: firstPercent, text: `${first} ${firstPercent}%` }}
        accessibilityActions={[
          { name: 'increment', label: `偏向 ${first}` },
          { name: 'decrement', label: `偏向 ${second}` },
        ]}
        onAccessibilityAction={(event) => {
          if (event.nativeEvent.actionName === 'increment') setFromX((ratio + 0.05) * travel + THUMB / 2);
          else if (event.nativeEvent.actionName === 'decrement')
            setFromX((ratio - 0.05) * travel + THUMB / 2);
        }}
        onLayout={onLayout}
        onStartShouldSetResponder={() => true}
        onMoveShouldSetResponder={() => true}
        onResponderGrant={onPointer}
        onResponderMove={onPointer}
        style={styles.track}>
        {trackWidth > 0 ? (
          <>
            <View style={[styles.rail, { backgroundColor: colors.surfaceContainerHighest }]} />
            <View
              style={[
                styles.fill,
                { width: ratio * travel + THUMB / 2, backgroundColor: colors.now },
              ]}
            />
            <View
              style={[
                styles.thumb,
                {
                  left: ratio * travel,
                  backgroundColor: colors.now,
                  borderColor: colors.surfaceContainerLowest,
                },
              ]}
            />
          </>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: Space.xs,
  },
  labels: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
  },
  labelGroup: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: Space.sm,
  },
  letter: {
    fontFamily: Fonts.mono,
    fontSize: Type.titleSmall,
    fontWeight: '600',
  },
  percent: {
    fontFamily: Fonts.mono,
    fontSize: Type.labelMedium,
  },
  track: {
    height: TRACK_HEIGHT,
  },
  rail: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: (TRACK_HEIGHT - FILL_HEIGHT) / 2,
    height: FILL_HEIGHT,
    borderRadius: Radius.pill,
  },
  fill: {
    position: 'absolute',
    left: 0,
    top: (TRACK_HEIGHT - FILL_HEIGHT) / 2,
    height: FILL_HEIGHT,
    borderRadius: Radius.pill,
  },
  thumb: {
    position: 'absolute',
    top: (TRACK_HEIGHT - THUMB) / 2,
    width: THUMB,
    height: THUMB,
    borderRadius: Radius.pill,
    borderWidth: 3,
  },
});
