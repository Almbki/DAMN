import { ScrollView, StyleSheet, Text, View } from 'react-native';

import type { InsightRead } from '@/api/types';
import { Radius, Space, Type } from '@/constants/tokens';
import { parseISO } from '@/domain/date';
import { useTheme } from '@/state/theme';

const LOAD_ORDER = ['high', 'medium', 'low'] as const;
const LOAD_LABEL: Record<(typeof LOAD_ORDER)[number], string> = {
  high: '高',
  medium: '中',
  low: '低',
};

/**
 * Task data panel. Every field maps 1:1 to the backend `InsightRead` returned by
 * `GET /plans/{plan_id}/insights`, so wiring the HTTP adapter later is a data
 * source swap.
 */
export function InsightPanel({ insight }: { insight: InsightRead }) {
  const { colors } = useTheme();
  const rate = Math.round(insight.completion_rate * 100);
  const minutesMax = Math.max(insight.total_planned_minutes, insight.total_actual_minutes, 1);
  const loadMax = Math.max(1, ...Object.values(insight.cognitive_load_breakdown));
  const ratio = insight.predicted_vs_actual_ratio;

  return (
    <View style={styles.wrap}>
      <View style={styles.summary}>
        <View style={styles.heroRow}>
          <Text style={[styles.hero, { color: colors.ink }]}>{rate}</Text>
          <Text style={[styles.heroUnit, { color: colors.inkMuted }]}>%</Text>
        </View>
        <Text style={[styles.note, { color: colors.inkMuted }]}>
          完成率 · {insight.completed_tasks}/{insight.total_tasks} 件
        </Text>
      </View>

      <Section title="计划 vs 实际">
        <CompareRow label="计划时长" value={insight.total_planned_minutes} max={minutesMax} unit="分钟" />
        <CompareRow label="实际时长" value={insight.total_actual_minutes} max={minutesMax} unit="分钟" />
        <Text style={[styles.note, { color: colors.inkMuted }]}>
          预估/实际比值 {ratio ?? '—'}
          {ratio == null ? '' : ratio > 1.3 ? '（偏慢）' : ratio < 0.7 ? '（偏快）' : '（接近）'}
        </Text>
      </Section>

      <Section title="认知负荷">
        {LOAD_ORDER.map((key) => (
          <CompareRow
            key={key}
            label={LOAD_LABEL[key]}
            value={insight.cognitive_load_breakdown[key] ?? 0}
            max={loadMax}
            unit="件"
          />
        ))}
        <Text style={[styles.note, { color: colors.inkMuted }]}>
          高认知合计 <Text style={styles.mono}>{insight.high_cognitive_minutes}</Text> 分钟
        </Text>
      </Section>

      <View style={styles.statRow}>
        <Stat label="平均压力" value={insight.avg_stress} suffix="/10" />
        <Stat label="平均精力" value={insight.avg_energy} suffix="/10" />
      </View>

      <Section title="每日完成">
        {insight.daily.length === 0 ? (
          <Text style={[styles.note, { color: colors.inkMuted }]}>还没有带日期的任务。</Text>
        ) : (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.dailyRow}>
            {insight.daily.map((day) => (
              <View key={day.date} style={styles.dailyCol}>
                <Text style={[styles.dailyValue, { color: colors.ink }]}>{day.completed_tasks}</Text>
                <View style={[styles.dailyTrack, { backgroundColor: colors.line }]}>
                  <View
                    style={[
                      styles.dailyFill,
                      {
                        backgroundColor: colors.ink,
                        height: `${Math.round(day.completion_rate * 100)}%`,
                      },
                    ]}
                  />
                </View>
                <Text style={[styles.dailyLabel, { color: colors.inkMuted }]}>
                  {parseISO(day.date).getMonth() + 1}/{parseISO(day.date).getDate()}
                </Text>
              </View>
            ))}
          </ScrollView>
        )}
      </Section>

      <Section title="建议">
        {insight.recommendations.length === 0 ? (
          <Text style={[styles.note, { color: colors.inkMuted }]}>暂无建议，保持现在的节奏。</Text>
        ) : (
          insight.recommendations.map((text) => (
            <View key={text} style={styles.bullet}>
              <View style={[styles.dot, { backgroundColor: colors.ink }]} />
              <Text style={[styles.bulletText, { color: colors.inkMuted }]}>{text}</Text>
            </View>
          ))
        )}
      </Section>
    </View>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const { colors } = useTheme();
  return (
    <View style={styles.section}>
      <Text style={[styles.sectionTitle, { color: colors.inkMuted }]}>{title}</Text>
      {children}
    </View>
  );
}

function CompareRow({
  label,
  value,
  max,
  unit,
}: {
  label: string;
  value: number;
  max: number;
  unit: string;
}) {
  const { colors } = useTheme();
  const ratio = max === 0 ? 0 : Math.min(1, value / max);
  return (
    <View style={styles.compareRow}>
      <Text style={[styles.compareLabel, { color: colors.ink }]}>{label}</Text>
      <View style={[styles.compareTrack, { backgroundColor: colors.line }]}>
        <View style={[styles.compareFill, { backgroundColor: colors.ink, width: `${ratio * 100}%` }]} />
      </View>
      <Text style={[styles.compareValue, { color: colors.inkMuted }]}>
        {value} {unit}
      </Text>
    </View>
  );
}

function Stat({ label, value, suffix }: { label: string; value: number | null; suffix: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.stat}>
      <Text style={[styles.statValue, { color: colors.ink }]}>
        {value ?? '—'}
        {value == null ? '' : <Text style={styles.statSuffix}> {suffix}</Text>}
      </Text>
      <Text style={[styles.statLabel, { color: colors.inkMuted }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: Space.xl,
  },
  mono: {
    fontFamily: 'IBMPlexMono_500Medium',
  },
  summary: {
    gap: Space.xs,
  },
  heroRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Space.xs,
  },
  hero: {
    fontSize: 44,
    lineHeight: 46,
    fontFamily: 'IBMPlexMono_500Medium',
  },
  heroUnit: {
    fontSize: Type.title,
    paddingBottom: 6,
  },
  note: {
    fontSize: Type.small,
    lineHeight: Type.small * 1.6,
  },
  section: {
    gap: Space.md,
  },
  sectionTitle: {
    fontSize: Type.small,
  },
  compareRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
  },
  compareLabel: {
    width: 64,
    fontSize: Type.small,
  },
  compareTrack: {
    flex: 1,
    height: 12,
    borderRadius: Radius.sm,
    overflow: 'hidden',
  },
  compareFill: {
    height: '100%',
    borderRadius: Radius.sm,
  },
  compareValue: {
    width: 78,
    textAlign: 'right',
    fontSize: Type.small,
    fontFamily: 'IBMPlexMono_400Regular',
  },
  statRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.xxl,
  },
  stat: {
    gap: Space.xs,
  },
  statValue: {
    fontSize: Type.heading,
    fontFamily: 'IBMPlexMono_500Medium',
  },
  statSuffix: {
    fontSize: Type.small,
    fontFamily: 'IBMPlexMono_400Regular',
  },
  statLabel: {
    fontSize: Type.small,
  },
  dailyRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Space.sm,
    paddingVertical: Space.xs,
  },
  dailyCol: {
    width: 34,
    alignItems: 'center',
    gap: Space.xs,
  },
  dailyValue: {
    fontSize: Type.micro,
    fontFamily: 'IBMPlexMono_400Regular',
  },
  dailyTrack: {
    width: 14,
    height: 64,
    borderRadius: Radius.sm,
    justifyContent: 'flex-end',
    overflow: 'hidden',
  },
  dailyFill: {
    width: '100%',
    borderRadius: Radius.sm,
  },
  dailyLabel: {
    fontSize: Type.micro,
  },
  bullet: {
    flexDirection: 'row',
    gap: Space.sm,
  },
  dot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    marginTop: 7,
  },
  bulletText: {
    flex: 1,
    fontSize: Type.small,
    lineHeight: Type.small * 1.6,
  },
});
