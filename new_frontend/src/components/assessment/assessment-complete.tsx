import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { TraitDomainKey, TraitSnapshot } from '@/api/types';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { EmptyState } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import {
  TRAIT_META,
  TRAIT_ORDER,
  asTraitSnapshot,
  traitBand,
  traitPosition,
  uncertaintyLabel,
} from '@/domain/traits';
import { useTheme } from '@/state/theme';

/** Completion summary. Presents relative model estimates, never percentiles. */
export function AssessmentComplete({
  traitProfile,
  onBack,
  onRestart,
}: {
  traitProfile: Record<string, unknown> | null;
  onBack: () => void;
  onRestart: () => void;
}) {
  const { colors } = useTheme();
  const [showTechnical, setShowTechnical] = useState(false);
  const trait = asTraitSnapshot(traitProfile);

  if (!trait) {
    return (
      <EmptyState
        title="测评已提交，但画像读取失败"
        body="结果已经保存在后端。稍后回到画像页刷新即可；如果仍然没有显示，请检查模型运行时。"
        actionLabel="返回画像"
        actionIcon="arrowRight"
        onAction={onBack}
      />
    );
  }

  return (
    <View style={styles.wrap}>
      <Surface level="level1" radius="lg">
        <View style={styles.hero}>
          <Text style={[styles.title, { color: colors.ink }]}>初始画像完成</Text>
          <Text style={[styles.body, { color: colors.inkMuted }]}>
            这是五个维度的模型估计。它描述相对位置，不是百分制，也不是心理诊断。后续执行和反馈会继续更新当前状态，但不会改写这份稳定特征。
          </Text>
        </View>
      </Surface>

      <View style={styles.grid}>
        {TRAIT_ORDER.map((key) => (
          <TraitResult key={key} domain={key} trait={trait} />
        ))}
      </View>

      <View style={styles.actions}>
        <Button
          label={showTechnical ? '收起技术详情' : '查看技术详情'}
          variant="text"
          size="sm"
          onPress={() => setShowTechnical((value) => !value)}
        />
        <View style={styles.actionButtons}>
          <Button label="返回画像" variant="filled" onPress={onBack} />
          <Button label="重新测评" variant="text" onPress={onRestart} />
        </View>
      </View>

      {showTechnical ? (
        <Surface level="level0" radius="md" bordered>
          <View style={styles.technical}>
            <Text style={[styles.technicalTitle, { color: colors.ink }]}>模型技术详情</Text>
            <Text style={[styles.note, { color: colors.inkMuted }]}>
              {trait.metadata.model_version} · {trait.metadata.artifact_version} ·{' '}
              {trait.metadata.artifact_hash.slice(0, 12)}…
            </Text>
            {TRAIT_ORDER.map((key) => {
              const domain = trait.domains[key];
              return (
                <Text key={key} style={[styles.mono, { color: colors.inkMuted }]}>
                  {key}: theta={domain.theta.toFixed(3)} · SE={domain.se.toFixed(3)} · CI95=
                  {domain.ci95
                    ? `[${domain.ci95[0].toFixed(2)}, ${domain.ci95[1].toFixed(2)}]`
                    : '—'}{' '}
                  · items={domain.items_answered}
                </Text>
              );
            })}
          </View>
        </Surface>
      ) : null}
    </View>
  );
}

function TraitResult({ domain, trait }: { domain: TraitDomainKey; trait: TraitSnapshot }) {
  const { colors } = useTheme();
  const meta = TRAIT_META[domain];
  const value = trait.domains[domain];
  return (
    <Surface level="level1" radius="lg" style={styles.card}>
      <View style={styles.cardInner}>
        <View style={styles.cardHead}>
          <Text style={[styles.cardTitle, { color: colors.ink }]}>{meta.name}</Text>
          <Text style={[styles.band, { color: colors.primary }]}>{traitBand(value.theta)}</Text>
        </View>
        <Progress value={traitPosition(value.theta)} height={6} color={colors.primary} />
        <Text style={[styles.note, { color: colors.inkMuted }]}>{meta.description}</Text>
        <Text style={[styles.meta, { color: colors.inkFaint }]}>
          模型不确定性 {value.se.toFixed(2)}（{uncertaintyLabel(value.se)}）
        </Text>
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: Space.xl },
  hero: { padding: Space.xl, gap: Space.md },
  title: { fontSize: Type.headlineSmall, fontWeight: '600' },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 640,
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: Space.md },
  card: { flexGrow: 1, flexBasis: 220, minWidth: 180 },
  cardInner: { padding: Space.lg, gap: Space.sm },
  cardHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.sm,
  },
  cardTitle: { fontSize: Type.titleMedium, fontWeight: '600' },
  band: { fontSize: Type.labelLarge, fontWeight: '600' },
  note: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  meta: { fontSize: Type.labelSmall, lineHeight: Type.labelSmall * Line.normal },
  actions: { gap: Space.md },
  actionButtons: { flexDirection: 'row', flexWrap: 'wrap', gap: Space.md },
  technical: { padding: Space.lg, gap: Space.xs },
  technicalTitle: { fontSize: Type.titleSmall, fontWeight: '600' },
  mono: { fontFamily: Fonts.mono, fontSize: Type.labelSmall },
});