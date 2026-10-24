import { useRouter, type Href } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import type { StateEstimate } from '@/api/types';
import { Progress } from '@/components/ui/progress';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { useProfile } from '@/state/profile';
import { useTheme } from '@/state/theme';

const STATE_META = [
  {
    key: 'fatigue' as const,
    label: '疲劳',
    description: '当前疲惫程度；越高越需要轻一点的任务。',
  },
  {
    key: 'stress' as const,
    label: '压力',
    description: '当前压力感受；持续偏高时系统会压低负荷。',
  },
  {
    key: 'self_efficacy' as const,
    label: '自我效能',
    description: '对完成任务的信心；来自执行结果和反思证据。',
  },
];

/** Level 2 dynamic state. Missing data is an explicit empty state. */
export function DynamicStateSection() {
  const { colors } = useTheme();
  const router = useRouter();
  const { model, loading, error, refresh } = useProfile();
  const state = model?.state ?? null;
  const hasTrait = model?.trait != null;

  return (
    <View style={styles.section}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: colors.ink }]}>当前状态</Text>
        <Text style={[styles.source, { color: colors.inkFaint }]}>动态状态 · Level 2</Text>
      </View>
      <Text style={[styles.body, { color: colors.inkMuted }]}>
        由真实执行记录和每日反馈更新的模型估计，不是每日反馈原值，也不是临床量表。
      </Text>

      {loading ? (
        <LoadingState label="正在读取当前状态…" />
      ) : error ? (
        <ErrorState title="当前状态读取失败" body={error} onRetry={refresh} />
      ) : state == null ? (
        hasTrait ? (
          <EmptyState
            title="当前状态数据不足"
            body="完成今天的任务并提交一次反馈后，系统才能估计你的疲劳、压力和自我效能。"
            actionLabel="去写今日反馈"
            actionIcon="flag"
            onAction={() => router.push('/feedback')}
          />
        ) : (
          <EmptyState
            title="先完成初始画像"
            body="动态状态需要以稳定的初始画像为基础。完成初始画像后，执行和反馈才会开始形成当前状态。"
            actionLabel="完成初始画像"
            actionIcon="arrowRight"
            onAction={() => router.push('/assessment' as Href)}
          />
        )
      ) : (
        <>
          <View style={styles.grid}>
            {STATE_META.map((meta) => (
              <StateCard key={meta.key} meta={meta} estimate={state[meta.key]} />
            ))}
          </View>
          <View style={styles.footer}>
            <Text style={[styles.meta, { color: colors.inkMuted }]}>
              观察日期 {state.date} · 模型 {state.model_version}
            </Text>
            <Text style={[styles.meta, { color: colors.inkFaint }]}>
              {state.cold_start ? '刚开始估计，参考价值有限' : '已基于真实历史更新'}
            </Text>
          </View>
          <Text style={[styles.note, { color: colors.inkFaint }]}>
            这里的 0–1 是模型内部状态尺度，不是百分比，也不代表“正常/异常”。
          </Text>
        </>
      )}
    </View>
  );
}

type StateMeta = (typeof STATE_META)[number];

function StateCard({ meta, estimate }: { meta: StateMeta; estimate: StateEstimate }) {
  const { colors } = useTheme();
  const value = Math.min(1, Math.max(0, estimate.value));
  return (
    <Surface level="level1" radius="lg" style={styles.card}>
      <View style={styles.cardInner}>
        <View style={styles.cardHead}>
          <Text style={[styles.cardTitle, { color: colors.ink }]}>{meta.label}</Text>
          <Text style={[styles.value, { color: colors.ink }]}>{value.toFixed(2)}</Text>
        </View>
        <Progress value={value} height={6} color={colors.primary} />
        <Text style={[styles.note, { color: colors.inkMuted }]}>{meta.description}</Text>
        <View style={styles.pills}>
          <Text style={[styles.pill, { color: colors.inkMuted, borderColor: colors.outline }]}>
            不确定性 ±{estimate.uncertainty.toFixed(2)}
          </Text>
          <Text style={[styles.pill, { color: colors.inkMuted, borderColor: colors.outline }]}>
            证据 {estimate.evidence_count}
          </Text>
          {estimate.conflict ? (
            <Text style={[styles.pill, { color: colors.warning, borderColor: colors.warning }]}>
              证据有冲突
            </Text>
          ) : null}
        </View>
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
  value: { fontFamily: Fonts.mono, fontSize: Type.titleLarge },
  note: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  meta: { fontSize: Type.labelSmall, lineHeight: Type.labelSmall * Line.normal },
  footer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: Space.sm,
  },
  pills: { flexDirection: 'row', flexWrap: 'wrap', gap: Space.xs },
  pill: {
    borderWidth: 1,
    borderRadius: Radius.pill,
    paddingHorizontal: Space.sm,
    paddingVertical: 2,
    fontSize: Type.labelSmall,
    overflow: 'hidden',
  },
});