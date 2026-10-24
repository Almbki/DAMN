import { useRouter, type Href } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { isApiError } from '@/api/client';
import { getReassessmentEligibility, startTraitAssessment } from '@/api/endpoints';
import type { TraitDomainKey } from '@/api/types';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { EmptyState, ErrorState, InlineNotice, LoadingState } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import {
  TRAIT_META,
  TRAIT_ORDER,
  traitBand,
  traitPosition,
  uncertaintyLabel,
} from '@/domain/traits';
import { useProfile } from '@/state/profile';
import { useTheme } from '@/state/theme';

/** Level 1 stable traits. Unavailable is a CTA, never fake defaults. */
export function TraitOverviewSection() {
  const { colors } = useTheme();
  const router = useRouter();
  const { model, loading, error, refresh } = useProfile();
  const [showTechnical, setShowTechnical] = useState(false);
  const [reassessOpen, setReassessOpen] = useState(false);
  const [reassessBusy, setReassessBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const trait = model?.trait ?? null;

  function formatEligibleDate(value: string | null): string {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString('zh-CN');
  }

  async function beginReassessment() {
    setReassessBusy(true);
    setNotice(null);
    try {
      const eligibility = await getReassessmentEligibility();
      if (!eligibility.eligible) {
        const next = formatEligibleDate(eligibility.next_eligible_at);
        setNotice(
          next
            ? `长期特征画像近期已更新，下次可重新测评：${next}`
            : '长期特征画像近期已更新。',
        );
        return;
      }
      setReassessOpen(true);
    } catch (caught) {
      setNotice(isApiError(caught) ? caught.message : '暂时无法重新测评。');
    } finally {
      setReassessBusy(false);
    }
  }

  async function confirmReassessment() {
    setReassessOpen(false);
    setReassessBusy(true);
    try {
      await startTraitAssessment(true);
      router.push('/assessment' as Href);
    } catch (caught) {
      setNotice(isApiError(caught) ? caught.message : '暂时无法重新测评。');
    } finally {
      setReassessBusy(false);
    }
  }

  return (
    <View style={styles.section}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: colors.ink }]}>稳定特征</Text>
        <Text style={[styles.source, { color: colors.inkFaint }]}>初始画像 · Level 1</Text>
      </View>
      <Text style={[styles.body, { color: colors.inkMuted }]}>
        来自初始画像测评，描述比较稳定的个人倾向。它是模型估计的相对位置，不是百分制，也不是心理诊断。
      </Text>

      {loading ? (
        <LoadingState label="正在读取初始画像…" />
      ) : error ? (
        <ErrorState title="初始画像读取失败" body={error} onRetry={refresh} />
      ) : trait == null ? (
        <EmptyState
          title="还没有初始画像"
          body="完成一次简短的初始画像测评，系统才能了解比较稳定的个人特征，并在后续计划里参考它。"
          actionLabel="完成初始画像"
          actionIcon="arrowRight"
          onAction={() => router.push('/assessment' as Href)}
        />
      ) : (
        <>
          {notice ? (
            <InlineNotice message={notice} onDismiss={() => setNotice(null)} />
          ) : null}
          <View style={styles.grid}>
            {TRAIT_ORDER.map((key) => (
              <TraitCard key={key} domain={key} trait={trait} />
            ))}
          </View>
          <View style={styles.actions}>
            <Button
              label={showTechnical ? '收起技术详情' : '查看技术详情'}
              variant="text"
              size="sm"
              onPress={() => setShowTechnical((value) => !value)}
            />
            <Button
              label={reassessBusy ? '检查中…' : '重新测评'}
              variant="tonal"
              size="sm"
              disabled={reassessBusy}
              onPress={() => void beginReassessment()}
            />
          </View>
          {showTechnical ? (
            <Surface level="level0" radius="md" bordered>
              <View style={styles.technical}>
                <Text style={[styles.technicalTitle, { color: colors.ink }]}>
                  模型技术详情
                </Text>
                <Text style={[styles.note, { color: colors.inkMuted }]}>
                  模型 {trait.metadata.model_version} · artifact{' '}
                  {trait.metadata.artifact_version} · {trait.metadata.artifact_hash.slice(0, 12)}…
                </Text>
                {TRAIT_ORDER.map((key) => {
                  const domain = trait.domains[key];
                  return (
                    <Text
                      key={key}
                      style={[styles.mono, { color: colors.inkMuted }]}>
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
        </>
      )}

      <Dialog
        visible={reassessOpen}
        title="重新测评初始画像？"
        description="重新测评完成后将更新长期特征画像，后续状态估计和计划分析将使用新的画像。旧测评记录会保留。"
        onRequestClose={() => setReassessOpen(false)}
        actions={[
          { label: '取消', onPress: () => setReassessOpen(false) },
          {
            label: '重新测评',
            variant: 'filled',
            onPress: () => void confirmReassessment(),
          },
        ]}
      />
    </View>
  );
}

function TraitCard({ domain, trait }: { domain: TraitDomainKey; trait: NonNullable<ReturnType<typeof useProfile>['model']>['trait'] }) {
  const { colors } = useTheme();
  const meta = TRAIT_META[domain];
  const value = trait?.domains[domain];
  if (!value) return null;
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
          估计不确定性 {value.se.toFixed(2)}（{uncertaintyLabel(value.se)}）
        </Text>
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  section: { gap: Space.md },
  head: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
    flexWrap: 'wrap',
  },
  title: { fontSize: Type.titleLarge, fontWeight: '600' },
  source: { fontSize: Type.labelMedium },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 620,
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
  actions: { flexDirection: 'row', flexWrap: 'wrap' },
  technical: { padding: Space.lg, gap: Space.xs },
  technicalTitle: { fontSize: Type.titleSmall, fontWeight: '600' },
  mono: { fontFamily: Fonts.mono, fontSize: Type.labelSmall },
});