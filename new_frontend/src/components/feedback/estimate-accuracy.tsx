import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { dataSource } from '@/api/config';
import { getEstimateAccuracy } from '@/api/endpoints';
import { estimateAccuracyFromApi } from '@/api/mapper';
import type { EstimateAccuracySummary } from '@/api/types';
import { Progress } from '@/components/ui/progress';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Space, Type, type ThemeColors } from '@/constants/tokens';
import { parseISO, todayISO } from '@/domain/date';
import { useTheme } from '@/state/theme';

const WEEKDAY = ['日', '一', '二', '三', '四', '五', '六'];

/** Product copy for the actual/planned ratio (not a statistical claim). */
export function ratioCopy(ratio: number | null): string {
  if (ratio == null) return '还没有记录实际用时';
  if (ratio > 1.3) return `实际是计划的 ${ratio.toFixed(2)} 倍，估得偏乐观`;
  if (ratio < 0.7) return `实际是计划的 ${ratio.toFixed(2)} 倍，估得偏保守`;
  return `实际约为计划的 ${ratio.toFixed(2)} 倍，估得比较准`;
}

/** Inside 0.7–1.3 the estimate is usable; outside it deserves attention. */
function ratioColor(ratio: number | null, colors: ThemeColors): string {
  if (ratio == null) return colors.inkFaint;
  if (ratio > 1.3) return colors.warning;
  if (ratio < 0.7) return colors.inkMuted;
  return colors.primary;
}

function dateLabel(date: string): string {
  const parsed = parseISO(date);
  return `${date.slice(5)} 周${WEEKDAY[parsed.getDay()]}`;
}

type LoadState = 'loading' | 'ready' | 'empty' | 'error';

/**
 * 画像页：近 7 天「计划估时 vs 实际用时」。Self-fetches the Phase 5 endpoint so
 * a profile refresh always picks up the latest executions.
 */
export function EstimateAccuracySection() {
  const { colors } = useTheme();
  const [data, setData] = useState<EstimateAccuracySummary | null>(null);
  const [state, setState] = useState<LoadState>(dataSource === 'api' ? 'loading' : 'empty');

  useEffect(() => {
    if (dataSource !== 'api') return;
    let cancelled = false;
    void getEstimateAccuracy(7)
      .then((raw) => {
        if (cancelled) return;
        const summary = estimateAccuracyFromApi(raw);
        setData(summary);
        setState(summary ? 'ready' : 'empty');
      })
      .catch(() => {
        if (cancelled) return;
        setData(null);
        setState('error');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const totalRatio = data?.ratio ?? null;

  return (
    <View style={styles.section}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: colors.ink }]}>估时 vs 实际</Text>
        <Text style={[styles.source, { color: colors.inkFaint }]}>近 7 天 · 估时校准</Text>
      </View>
      <Text style={[styles.body, { color: colors.inkMuted }]}>
        计划分钟数和真实执行分钟的对比。点过开始的任务会按开始到完成的时长自动记录实际用时；
        没点开始的任务，晚上反馈时会问你估得准不准。
      </Text>

      {state === 'loading' ? (
        <Surface level="level0" radius="lg" bordered>
          <Text style={[styles.helperPadded, { color: colors.inkMuted }]}>正在读取估时对比…</Text>
        </Surface>
      ) : state === 'error' ? (
        <Surface level="level0" radius="lg" bordered>
          <Text style={[styles.helperPadded, { color: colors.inkMuted }]}>
            暂时读不到估时对比，稍后刷新再看。
          </Text>
        </Surface>
      ) : state === 'empty' || data == null ? (
        <Surface level="level0" radius="lg" bordered style={{ borderStyle: 'dashed' }}>
          <View style={styles.empty}>
            <Text style={[styles.emptyTitle, { color: colors.ink }]}>还没有可对比的记录</Text>
            <Text style={[styles.helper, { color: colors.inkMuted }]}>
              {dataSource === 'api'
                ? '完成任务并记录实际用时后，这里会按天显示计划和实际的差距。'
                : '演示模式没有真实执行记录；连接后端后，这里会显示近 7 天的估时对比。'}
            </Text>
          </View>
        </Surface>
      ) : (
        <Surface level="level1" radius="lg">
          <View style={styles.card}>
            {data.points.map((point) => {
              const color = ratioColor(point.ratio, colors);
              const fill =
                point.planned_minutes > 0
                  ? point.actual_minutes / point.planned_minutes
                  : point.actual_minutes > 0
                    ? 1
                    : 0;
              return (
                <View key={point.date} style={styles.day}>
                  <View style={[styles.dayHead, { borderTopColor: colors.outlineVariant }]}>
                    <Text style={[styles.date, { color: colors.inkMuted }]}>
                      {dateLabel(point.date)}
                    </Text>
                    <Text style={[styles.minutes, { color: colors.ink }]}>
                      计划 <Text style={styles.mono}>{point.planned_minutes}</Text> · 实际{' '}
                      <Text style={styles.mono}>{point.actual_minutes}</Text> 分
                    </Text>
                    <Text style={[styles.ratio, { color }]}>
                      {point.ratio == null ? '—' : `${point.ratio.toFixed(2)}×`}
                    </Text>
                  </View>
                  <Progress value={fill} height={6} color={color} />
                </View>
              );
            })}

            <View style={[styles.total, { borderTopColor: colors.outlineVariant }]}>
              <Text style={[styles.minutes, { color: colors.ink }]}>
                合计：计划 <Text style={styles.mono}>{data.planned_minutes}</Text> 分 · 实际{' '}
                <Text style={styles.mono}>{data.actual_minutes}</Text> 分
              </Text>
              <Text style={[styles.totalNote, { color: ratioColor(totalRatio, colors) }]}>
                {ratioCopy(totalRatio)}
              </Text>
            </View>
          </View>
        </Surface>
      )}
    </View>
  );
}

/**
 * 反馈页结果卡：只显示今天一行「估时 vs 实际」。失败或今天没有数据时静默
 * 不渲染，避免打扰提交成功的主信息。
 */
export function TodayEstimateCard() {
  const { colors } = useTheme();
  const [data, setData] = useState<EstimateAccuracySummary | null>(null);

  useEffect(() => {
    if (dataSource !== 'api') return;
    let cancelled = false;
    void getEstimateAccuracy(1)
      .then((raw) => {
        if (!cancelled) setData(estimateAccuracyFromApi(raw));
      })
      .catch(() => {
        if (!cancelled) setData(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const point =
    data?.points.find((entry) => entry.date === todayISO()) ??
    data?.points[data.points.length - 1] ??
    null;
  if (!point) return null;
  if (point.planned_minutes === 0 && point.actual_minutes === 0) return null;

  const color = ratioColor(point.ratio, colors);
  const fill =
    point.planned_minutes > 0
      ? point.actual_minutes / point.planned_minutes
      : point.actual_minutes > 0
        ? 1
        : 0;

  return (
    <Surface level="level0" radius="lg" bordered>
      <View style={styles.today}>
        <View style={styles.todayHead}>
          <Text style={[styles.todayTitle, { color: colors.ink }]}>今天估时 vs 实际</Text>
          <Text style={[styles.ratio, { color }]}>
            {point.ratio == null ? '—' : `${point.ratio.toFixed(2)}×`}
          </Text>
        </View>
        <View style={styles.dayHeadInline}>
          <Text style={[styles.minutes, { color: colors.ink }]}>
            计划 <Text style={styles.mono}>{point.planned_minutes}</Text> 分 · 实际{' '}
            <Text style={styles.mono}>{point.actual_minutes}</Text> 分
          </Text>
        </View>
        <Progress value={fill} height={6} color={color} />
        <Text style={[styles.helper, { color: colors.inkMuted }]}>{ratioCopy(point.ratio)}</Text>
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: Space.md,
  },
  head: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
    flexWrap: 'wrap',
  },
  title: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  source: {
    fontSize: Type.labelMedium,
  },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 620,
  },
  card: {
    padding: Space.lg,
    gap: Space.md,
  },
  day: {
    gap: Space.xs,
  },
  dayHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    flexWrap: 'wrap',
    gap: Space.md,
    borderTopWidth: 1,
    paddingTop: Space.sm,
  },
  date: {
    fontFamily: Fonts.mono,
    fontSize: Type.labelMedium,
    minWidth: 74,
  },
  minutes: {
    flexGrow: 1,
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
  },
  mono: {
    fontFamily: Fonts.mono,
  },
  ratio: {
    fontFamily: Fonts.mono,
    fontSize: Type.bodyMedium,
  },
  total: {
    borderTopWidth: 1,
    paddingTop: Space.md,
    gap: Space.xs,
  },
  totalNote: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  helper: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  helperPadded: {
    padding: Space.lg,
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  empty: {
    padding: Space.lg,
    gap: Space.xs,
  },
  emptyTitle: {
    fontSize: Type.bodyLarge,
    fontWeight: '600',
  },
  today: {
    padding: Space.lg,
    gap: Space.sm,
  },
  todayHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  todayTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  dayHeadInline: {
    flexDirection: 'row',
    alignItems: 'baseline',
    flexWrap: 'wrap',
    gap: Space.md,
  },
});
