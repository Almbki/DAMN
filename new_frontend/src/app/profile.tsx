import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { DynamicStateSection } from '@/components/profile/dynamic-state';
import { TraitOverviewSection } from '@/components/profile/trait-overview';
import { TrendChart } from '@/components/trend-chart';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

export default function ProfileScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { situation, stats, refresh, loading, mode } = usePlan();

  return (
    <View style={styles.page}>
      <View style={styles.toolbar}>
        <Text style={[styles.toolbarText, { color: colors.inkMuted }]}>
          {mode === 'api'
            ? '稳定特征来自真实初始画像；当前状态来自执行与反馈更新的 Level 2 模型；下方趋势才是每日反馈原值。三者不是同一个概念。'
            : '演示模式：显示的是本机示例数据。连接后端后，这里会显示真实初始画像、当前状态与每日反馈趋势。'}
        </Text>
        <Button
          label={loading ? '刷新中…' : '刷新数据'}
          variant="tonal"
          size="sm"
          icon="refresh"
          disabled={loading || mode === 'mock'}
          onPress={refresh}
        />
      </View>

      <TraitOverviewSection />

      <DynamicStateSection />


      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.ink }]}>近期反馈趋势</Text>
        <Text style={[styles.note, { color: colors.inkMuted }]}>
          来自你每天写下的精力、压力和完成情况，是原始反馈走势，不是 Level 2 模型状态。
        </Text>
        {situation.points.length >= 2 ? (
          <TrendChart points={situation.points} />
        ) : (
          <EmptyState
            title="还没有足够的每日反馈"
            body={`趋势至少要两天的反馈才能画出来，现在只有 ${situation.samples} 天。写完今天的状态，这里就会开始有线条。`}
            actionLabel="去待办写反馈"
            actionIcon="arrowRight"
            onAction={() => router.push('/')}
          />
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
  toolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  toolbarText: {
    flexGrow: 1,
    flexBasis: 320,
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 620,
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
