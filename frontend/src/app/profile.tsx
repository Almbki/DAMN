import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { TrendChart } from '@/components/trend-chart';
import { Button } from '@/components/ui/button';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

function levelLabel(value: number | null, kind: 'energy' | 'stress'): string {
  if (value == null) return '还没有数据';
  if (kind === 'energy') {
    if (value >= 6.5) return '精力不错';
    if (value <= 3.5) return '精力偏低';
    return '精力中等';
  }
  if (value >= 7) return '压力偏高';
  if (value <= 3) return '很放松';
  return '压力中等';
}

export default function ProfileScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { situation, stats, user, energyLabelText } = usePlan();

  const energy = situation.energy;
  const stress = situation.stress;
  const efficacyPercent = Math.round(situation.efficacy * 100);

  return (
    <View style={styles.page}>
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.ink }]}>当前状态</Text>
        <View style={styles.tiles}>
          <Tile
            title="精力"
            value={energy == null ? '—' : energy.toFixed(1)}
            unit={energy == null ? '' : '/ 10'}
            note={levelLabel(energy, 'energy')}
            tone={colors.primary}
          />
          <Tile
            title="压力"
            value={stress == null ? '—' : stress.toFixed(1)}
            unit={stress == null ? '' : '/ 10'}
            note={levelLabel(stress, 'stress')}
            tone={colors.error}
          />
          <Tile
            title="效能"
            value={`${efficacyPercent}`}
            unit="%"
            note={`执行权重 ${user.execution_weight.toFixed(2)}`}
            tone={colors.ink}
          />
        </View>
        <Text style={[styles.note, { color: colors.inkMuted }]}>
          今天的节律：{energyLabelText}。
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.ink }]}>趋势（近 14 天）</Text>
        {situation.points.length >= 2 ? (
          <TrendChart points={situation.points} />
        ) : (
          <Text style={[styles.note, { color: colors.inkMuted }]}>
            至少要两天的反馈才能画趋势。
          </Text>
        )}
        <Surface level="level1" radius="md">
          <View style={styles.sufficiency}>
            <Text style={[styles.sufficiencyTitle, { color: colors.ink }]}>
              {situation.sufficient ? '数据够用' : '数据还不够'}
            </Text>
            <Text style={[styles.note, { color: colors.inkMuted }]}>
              已有 <Text style={styles.mono}>{situation.samples}</Text> 天反馈，判断门槛是{' '}
              <Text style={styles.mono}>{situation.minSamples}</Text> 天。
              {situation.sufficient
                ? '现在的判断比较稳，趋势可以当参考。'
                : `再记 ${Math.max(0, situation.minSamples - situation.samples)} 天，系统会更有把握。`}
            </Text>
          </View>
        </Surface>
      </View>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.ink }]}>系统为什么这么判断</Text>
        <View style={styles.reasons}>
          {situation.reasons.map((reason) => (
            <View key={reason} style={styles.reason}>
              <View style={[styles.reasonRule, { backgroundColor: colors.now }]} />
              <Text style={[styles.reasonText, { color: colors.inkMuted }]}>{reason}</Text>
            </View>
          ))}
        </View>
      </View>

      <Surface level="level1" radius="lg">
        <View style={styles.facts}>
          <Fact label="已完成 / 未完成" value={`${stats.doneCount} / ${stats.openCount}`} />
          <Fact label="完成率" value={`${Math.round(stats.rate * 100)}%`} />
          <Fact label="连续完成" value={`${stats.streak} 天`} />
        </View>
      </Surface>

      <View style={styles.footer}>
        <Text style={[styles.note, { color: colors.inkMuted }]}>
          作息与每日可投入时间在「基础档案」里设置，改一次就一直生效。
        </Text>
        <Button
          label="基础档案"
          variant="tonal"
          icon="arrowRight"
          onPress={() => router.push('/profile-details')}
        />
      </View>
    </View>
  );
}

function Tile({
  title,
  value,
  unit,
  note,
  tone,
}: {
  title: string;
  value: string;
  unit: string;
  note: string;
  tone: string;
}) {
  const { colors } = useTheme();
  return (
    <Surface level="level1" radius="lg" style={styles.tileSurface}>
      <View style={styles.tile}>
        <Text style={[styles.tileTitle, { color: colors.inkMuted }]}>{title}</Text>
        <View style={styles.tileValueRow}>
          <Text style={[styles.tileValue, { color: tone }]}>{value}</Text>
          {unit ? <Text style={[styles.tileUnit, { color: colors.inkMuted }]}>{unit}</Text> : null}
        </View>
        <Text style={[styles.tileNote, { color: colors.inkMuted }]}>{note}</Text>
      </View>
    </Surface>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.fact}>
      <Text style={[styles.factLabel, { color: colors.inkMuted }]}>{label}</Text>
      <Text style={[styles.factValue, { color: colors.ink }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: Space.xxl,
  },
  section: {
    gap: Space.md,
  },
  sectionTitle: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  tiles: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  tileSurface: {
    flexGrow: 1,
    flexBasis: 180,
    minWidth: 150,
  },
  tile: {
    padding: Space.lg,
    gap: Space.xs,
  },
  tileTitle: {
    fontSize: Type.labelLarge,
  },
  tileValueRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Space.xs,
  },
  tileValue: {
    fontFamily: Fonts.mono,
    fontSize: Type.displaySmall,
    lineHeight: Type.displaySmall * 1.05,
  },
  tileUnit: {
    fontSize: Type.labelMedium,
    paddingBottom: 6,
  },
  tileNote: {
    fontSize: Type.labelMedium,
  },
  note: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 600,
  },
  mono: {
    fontFamily: Fonts.mono,
  },
  sufficiency: {
    padding: Space.lg,
    gap: Space.xs,
  },
  sufficiencyTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  reasons: {
    gap: Space.md,
  },
  reason: {
    flexDirection: 'row',
    gap: Space.md,
  },
  reasonRule: {
    width: 3,
    borderRadius: 2,
  },
  reasonText: {
    flex: 1,
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 600,
  },
  facts: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.xxl,
    padding: Space.lg,
  },
  fact: {
    gap: Space.xs,
  },
  factLabel: {
    fontSize: Type.labelMedium,
  },
  factValue: {
    fontFamily: Fonts.mono,
    fontSize: Type.titleLarge,
  },
  footer: {
    gap: Space.md,
    alignItems: 'flex-start',
  },
});
