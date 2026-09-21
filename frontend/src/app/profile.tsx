import { StyleSheet, Text, View } from 'react-native';

import { Surface } from '@/components/surface';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { mockProfile } from '@/data/mock';
import { parseISO } from '@/domain/date';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

const WEEKDAY = ['日', '一', '二', '三', '四', '五', '六'];

export default function ProfileScreen() {
  const { colors } = useTheme();
  const { stats } = usePlan();

  const max = Math.max(1, ...stats.weekly.map((bucket) => bucket.count));

  return (
    <View style={styles.page}>
      <View style={styles.cells}>
        <StatCell label="精力" value={mockProfile.energy.value} level={mockProfile.energy.level} />
        <StatCell label="压力" value={mockProfile.stress.value} level={mockProfile.stress.level} />
        <StatCell
          label="效能"
          value={mockProfile.performance.value}
          level={mockProfile.performance.level}
        />
      </View>

      <Surface elevation="raised" radius={Radius.lg} style={styles.card}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>最近 7 天</Text>
        <View style={styles.bars}>
          {stats.weekly.map((bucket, index) => {
            const ratio = bucket.count / max;
            const isToday = index === stats.weekly.length - 1;
            return (
              <View key={bucket.date} style={styles.barCol}>
                <Text style={[styles.barValue, { color: colors.inkMuted }]}>{bucket.count}</Text>
                <View style={[styles.barTrack, { backgroundColor: colors.panel }]}>
                  <View
                    style={[
                      styles.barFill,
                      {
                        height: `${Math.round(ratio * 100)}%`,
                        backgroundColor: isToday ? colors.accent : colors.inkMuted,
                      },
                    ]}
                  />
                </View>
                <Text style={[styles.barLabel, { color: colors.inkMuted }]}>
                  周{WEEKDAY[parseISO(bucket.date).getDay()]}
                </Text>
              </View>
            );
          })}
        </View>
        <Text style={[styles.note, { color: colors.inkMuted }]}>
          已有 {mockProfile.dataDays} 天数据，趋势可信。
        </Text>
      </Surface>

      <View style={styles.why}>
        <View style={[styles.whyRule, { backgroundColor: colors.accent }]} />
        <View style={styles.whyBody}>
          <Text style={[styles.cardTitle, { color: colors.ink }]}>系统为什么这么判断</Text>
          <Text style={[styles.whyText, { color: colors.inkMuted }]}>{mockProfile.attribution}</Text>
        </View>
      </View>
    </View>
  );
}

function StatCell({ label, value, level }: { label: string; value: number; level: string }) {
  const { colors } = useTheme();
  return (
    <Surface elevation="raised" radius={Radius.lg} style={styles.cell}>
      <Text style={[styles.cellLabel, { color: colors.inkMuted }]}>{label}</Text>
      <Text style={[styles.cellValue, { color: colors.ink }]}>{value}</Text>
      <Text style={[styles.cellLevel, { color: colors.inkMuted }]}>{level}</Text>
    </Surface>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: Space.xl,
  },
  cells: {
    flexDirection: 'row',
    gap: Space.sm,
  },
  cell: {
    flex: 1,
    padding: Space.lg,
    gap: Space.xs,
  },
  cellLabel: {
    fontSize: Type.small,
  },
  cellValue: {
    fontSize: Type.displaySm,
    lineHeight: Type.displaySm * 1.05,
    fontFamily: Fonts.mono,
  },
  cellLevel: {
    fontSize: Type.small,
  },
  card: {
    padding: Space.lg,
    gap: Space.md,
  },
  cardTitle: {
    fontSize: Type.title,
    fontWeight: '700',
  },
  bars: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Space.sm,
  },
  barCol: {
    flex: 1,
    alignItems: 'center',
    gap: Space.xs,
  },
  barValue: {
    fontSize: Type.micro,
    fontFamily: Fonts.monoRegular,
  },
  barTrack: {
    width: '100%',
    height: 72,
    borderRadius: Radius.xs,
    overflow: 'hidden',
    justifyContent: 'flex-end',
  },
  barFill: {
    width: '100%',
    borderRadius: Radius.xs,
  },
  barLabel: {
    fontSize: Type.micro,
  },
  note: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.relaxed,
  },
  why: {
    flexDirection: 'row',
    gap: Space.md,
  },
  whyRule: {
    width: 3,
    borderRadius: 2,
  },
  whyBody: {
    flex: 1,
    gap: Space.sm,
  },
  whyText: {
    fontSize: Type.body,
    lineHeight: Type.body * Line.relaxed,
    maxWidth: 560,
  },
});
