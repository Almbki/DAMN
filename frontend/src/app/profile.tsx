import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Segmented } from '@/components/ui/segmented';
import { Line, Radius, Space, Type } from '@/constants/tokens';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

const LEVELS = ['偏低', '一般', '不错', '很好'];
const MOODS = ['低落', '平静', '轻松', '愉快'];
const STRESS = ['很低', '中等', '偏高', '很高'];

export default function ProfileScreen() {
  const { colors } = useTheme();
  const { user, completedCount, totalCount } = usePlan();
  const [energy, setEnergy] = useState(1);
  const [mood, setMood] = useState(2);
  const [stress, setStress] = useState(1);

  return (
    <View style={styles.page}>
      <View style={[styles.card, { borderColor: colors.line }]}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>用户画像</Text>
        <Text style={[styles.cardBody, { color: colors.inkMuted }]}>
          基于历史执行数据生成的特征，用于估计任务耗时与每日安排量。
        </Text>
        <View style={styles.tags}>
          {['全栈开发', '极简主义', '高执行力', '晨间型'].map((tag) => (
            <View key={tag} style={[styles.tag, { borderColor: colors.line }]}>
              <Text style={[styles.tagText, { color: colors.ink }]}>{tag}</Text>
            </View>
          ))}
        </View>
        <View style={[styles.facts, { borderTopColor: colors.line }]}>
          <Fact label="账号" value={user.display_name ?? user.email} />
          <Fact label="执行权重" value={user.execution_weight.toFixed(2)} mono />
          <Fact label="本周完成" value={`${completedCount}/${totalCount}`} mono />
        </View>
      </View>

      <View style={[styles.card, { borderColor: colors.line }]}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>现在的状态</Text>
        <Segmented label="精力" options={LEVELS} value={energy} onChange={setEnergy} />
        <Segmented label="心情" options={MOODS} value={mood} onChange={setMood} />
        <Segmented label="压力" options={STRESS} value={stress} onChange={setStress} />
        <Text style={[styles.helper, { color: colors.inkMuted }]}>
          心情只影响今天的安排顺序，不会改变任务量。
        </Text>
      </View>
    </View>
  );
}

function Fact({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  const { colors } = useTheme();
  return (
    <View style={styles.fact}>
      <Text style={[styles.factLabel, { color: colors.inkMuted }]}>{label}</Text>
      <Text
        style={[
          styles.factValue,
          { color: colors.ink, fontFamily: mono ? 'IBMPlexMono_500Medium' : undefined },
        ]}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: Space.xxl,
  },
  card: {
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: Space.xl,
    gap: Space.lg,
  },
  cardTitle: {
    fontSize: Type.title,
    fontWeight: '700',
  },
  cardBody: {
    fontSize: Type.body,
    lineHeight: Type.body * Line.normal,
    maxWidth: 560,
  },
  tags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  tag: {
    borderWidth: 1,
    borderRadius: Radius.pill,
    paddingHorizontal: Space.md,
    paddingVertical: Space.xs,
  },
  tagText: {
    fontSize: Type.small,
  },
  facts: {
    borderTopWidth: 1,
    paddingTop: Space.lg,
    gap: Space.md,
  },
  fact: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: Space.lg,
  },
  factLabel: {
    fontSize: Type.body,
  },
  factValue: {
    fontSize: Type.body,
  },
  helper: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.relaxed,
  },
});
