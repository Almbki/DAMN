import { useState } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';

import { Fonts, Radius, Space, Type } from '@/constants/tokens';
import type { SituationPoint } from '@/domain/situation';
import { useTheme } from '@/state/theme';

const CHART_HEIGHT = 150;
const MAX = 10;

type Metric = { key: keyof Pick<SituationPoint, 'energy' | 'stress' | 'efficacy'>; label: string; color: string };

/**
 * A three-series trend line, drawn with positioned rotated Views (no SVG
 * dependency). Each segment is a width-`length` bar centred on the segment's
 * midpoint, so rotation needs no transform origin.
 */
export function TrendChart({ points }: { points: SituationPoint[] }) {
  const { colors } = useTheme();
  const [width, setWidth] = useState(0);

  const metrics: Metric[] = [
    { key: 'energy', label: '精力', color: colors.primary },
    { key: 'stress', label: '压力', color: colors.error },
    { key: 'efficacy', label: '效能', color: colors.ink },
  ];

  const onLayout = (event: LayoutChangeEvent) => setWidth(event.nativeEvent.layout.width);
  const count = points.length;
  const step = count > 1 ? width / (count - 1) : 0;
  const xFor = (index: number) => (count > 1 ? index * step : width / 2);
  const yFor = (value: number) => CHART_HEIGHT - (Math.min(MAX, Math.max(0, value)) / MAX) * CHART_HEIGHT;

  return (
    <View style={styles.wrap}>
      <View style={styles.legend}>
        {metrics.map((metric) => (
          <View key={metric.key} style={styles.legendItem}>
            <View style={[styles.legendDash, { backgroundColor: metric.color }]} />
            <Text style={[styles.legendLabel, { color: colors.inkMuted }]}>{metric.label}</Text>
          </View>
        ))}
      </View>

      <View
        onLayout={onLayout}
        style={[styles.plot, { borderBottomColor: colors.outlineVariant, height: CHART_HEIGHT }]}>
        {[0.25, 0.5, 0.75].map((fraction) => (
          <View
            key={fraction}
            style={[styles.gridline, { top: CHART_HEIGHT * fraction, backgroundColor: colors.outlineVariant }]}
          />
        ))}

        {width > 0
          ? metrics.map((metric) =>
              renderSeries(
                metric.key,
                metric.key === 'efficacy'
                  ? points.map((point) => (point.efficacy == null ? null : point.efficacy * MAX))
                  : points.map((point) => point[metric.key]),
                xFor,
                yFor,
                metric.color,
                2,
              ),
            )
          : null}
      </View>

      <View style={styles.axis}>
        <Text style={[styles.axisLabel, { color: colors.inkFaint }]}>{points[0]?.date.slice(5)}</Text>
        <Text style={[styles.axisLabel, { color: colors.inkFaint }]}>
          {points[count - 1]?.date.slice(5)}
        </Text>
      </View>
    </View>
  );
}

function renderSeries(
  prefix: string,
  values: (number | null)[],
  xFor: (index: number) => number,
  yFor: (value: number) => number,
  color: string,
  stroke: number,
) {
  const nodes: React.ReactNode[] = [];

  for (let index = 0; index < values.length; index += 1) {
    const value = values[index];
    if (value == null) continue;
    const x = xFor(index);
    const y = yFor(value);

    const previousIndex = previousNonNull(values, index);
    if (previousIndex != null) {
      const x1 = xFor(previousIndex);
      const y1 = yFor(values[previousIndex] as number);
      const length = Math.hypot(x - x1, y - y1);
      const angle = (Math.atan2(y - y1, x - x1) * 180) / Math.PI;
      nodes.push(
        <View
          key={`${prefix}-seg-${index}`}
          style={{
            position: 'absolute',
            left: (x1 + x) / 2 - length / 2,
            top: (y1 + y) / 2 - stroke / 2,
            width: length,
            height: stroke,
            borderRadius: stroke,
            backgroundColor: color,
            transform: [{ rotate: `${angle}deg` }],
          }}
        />,
      );
    }

    nodes.push(
      <View
        key={`${prefix}-dot-${index}`}
        style={{
          position: 'absolute',
          left: x - stroke * 1.5,
          top: y - stroke * 1.5,
          width: stroke * 3,
          height: stroke * 3,
          borderRadius: stroke * 3,
          backgroundColor: color,
        }}
      />,
    );
  }

  return nodes;
}

function previousNonNull(values: (number | null)[], index: number): number | null {
  for (let i = index - 1; i >= 0; i -= 1) {
    if (values[i] != null) return i;
  }
  return null;
}

const styles = StyleSheet.create({
  wrap: {
    gap: Space.sm,
  },
  legend: {
    flexDirection: 'row',
    gap: Space.lg,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
  },
  legendDash: {
    width: 14,
    height: 3,
    borderRadius: Radius.pill,
  },
  legendLabel: {
    fontSize: Type.labelMedium,
  },
  plot: {
    width: '100%',
    borderBottomWidth: 1,
    position: 'relative',
  },
  gridline: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 1,
  },
  axis: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  axisLabel: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelSmall,
  },
});
