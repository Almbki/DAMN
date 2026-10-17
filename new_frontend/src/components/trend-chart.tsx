import { useState } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';

import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { formatShort } from '@/domain/date';
import type { SituationPoint } from '@/domain/situation';
import { useTheme } from '@/state/theme';

const CHART_HEIGHT = 150;
const MAX = 10;
const Y_AXIS_WIDTH = 26;

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

  const first = points[0]?.date;
  const last = points[count - 1]?.date;
  const range = first && last ? `${formatShort(first)} — ${formatShort(last)}` : '暂无日期';
  const summary = `趋势图，${range}，共 ${count} 个数据点。精力与压力按 0 到 10 分绘制；效能按 0 到 100% 归一化绘制。`;

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

      <View style={styles.chartRow}>
        <View style={styles.yAxis} accessibilityElementsHidden importantForAccessibility="no">
          <Text style={[styles.axisTick, { color: colors.inkFaint }]}>10</Text>
          <Text style={[styles.axisTick, { color: colors.inkFaint }]}>5</Text>
          <Text style={[styles.axisTick, { color: colors.inkFaint }]}>0</Text>
        </View>

        <View
          accessible
          accessibilityRole="image"
          accessibilityLabel={summary}
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
      </View>

      <View style={styles.axis}>
        <Text style={[styles.axisLabel, { color: colors.inkFaint }]}>{points[0]?.date.slice(5)}</Text>
        <Text style={[styles.axisLabel, { color: colors.inkFaint }]}>
          {points[count - 1]?.date.slice(5)}
        </Text>
      </View>

      <Text style={[styles.unitNote, { color: colors.inkFaint }]}>
        精力 / 压力：0–10 分 · 效能：0–100%（按 0–10 归一化绘制）。最近 {count} 天有反馈。
      </Text>
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
    flexWrap: 'wrap',
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
  chartRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Space.sm,
  },
  yAxis: {
    width: Y_AXIS_WIDTH,
    height: CHART_HEIGHT,
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    paddingRight: 2,
  },
  axisTick: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelSmall,
    lineHeight: Type.labelSmall,
  },
  plot: {
    flex: 1,
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
    paddingLeft: Y_AXIS_WIDTH + Space.sm,
  },
  axisLabel: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelSmall,
  },
  unitNote: {
    fontSize: Type.labelSmall,
    lineHeight: Type.labelSmall * Line.normal,
    paddingLeft: Y_AXIS_WIDTH + Space.sm,
  },
});
