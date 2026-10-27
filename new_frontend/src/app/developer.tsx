import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { isApiError } from '@/api/client';
import {
  getMe,
  getModelRuntime,
  getSyntheticStatus,
  importSyntheticScenario,
  listSyntheticScenarios,
  resetSyntheticData,
} from '@/api/endpoints';
import type {
  ModelRuntimeRead,
  SyntheticImportSummary,
  SyntheticScenarioInfo,
  SyntheticStatus,
} from '@/api/types';
import { Button } from '@/components/ui/button';
import { EmptyState, ErrorState, InlineNotice, LoadingState } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { usePlan } from '@/state/plan';
import { useProfile } from '@/state/profile';
import { useSession } from '@/state/session';
import { useTheme } from '@/state/theme';

const LEVEL_LABEL: Record<string, string> = {
  level1: 'Level 1 · 稳定特征',
  level2: 'Level 2 · 动态状态',
  level3: 'Level 3 · 任务预测',
};

const STATUS_LABEL: Record<string, string> = {
  ok: '正常',
  degraded: '降级',
  unavailable: '不可用',
  not_fitted: '未拟合',
};

export default function DeveloperScreen() {
  const { colors } = useTheme();
  const { mode } = usePlan();
  const profile = useProfile();
  const { setUser, user } = useSession();
  const showcaseLocked = Boolean(user?.profile?.showcase_seed);
  const [data, setData] = useState<ModelRuntimeRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scenarios, setScenarios] = useState<SyntheticScenarioInfo[]>([]);
  const [syntheticStatus, setSyntheticStatus] = useState<SyntheticStatus | null>(null);
  const [syntheticEnabled, setSyntheticEnabled] = useState(false);
  const [scenarioBusy, setScenarioBusy] = useState<string | null>(null);
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [scenarioSummary, setScenarioSummary] = useState<SyntheticImportSummary | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setData(await getModelRuntime());
      try {
        const [list, status] = await Promise.all([
          listSyntheticScenarios(),
          getSyntheticStatus(),
        ]);
        setScenarios(list.scenarios);
        setSyntheticStatus(status);
        setSyntheticEnabled(true);
      } catch (caught) {
        if (isApiError(caught) && caught.status === 404) {
          setSyntheticEnabled(false);
        } else {
          setScenarioError(isApiError(caught) ? caught.message : 'Synthetic 状态读取失败');
        }
      }
    } catch (caught) {
      setError(isApiError(caught) ? caught.message : '模型运行时读取失败');
    } finally {
      setLoading(false);
    }
  }

  async function importScenario(name: string) {
    if (showcaseLocked) {
      setScenarioError('受保护的演示账号：Synthetic 导入已禁用。');
      return;
    }
    setScenarioBusy(name);
    setScenarioError(null);
    setScenarioSummary(null);
    try {
      const summary = await importSyntheticScenario(name);
      setScenarioSummary(summary);
      try {
        setUser(await getMe());
      } catch {
        // The import succeeded; the next bootstrap will refresh the session.
      }
      profile.refresh();
      await load();
    } catch (caught) {
      setScenarioError(isApiError(caught) ? caught.message : '导入失败');
    } finally {
      setScenarioBusy(null);
    }
  }

  async function resetSynthetic() {
    if (showcaseLocked) {
      setScenarioError('受保护的演示账号：Synthetic 重置已禁用。');
      return;
    }
    setScenarioBusy('reset');
    setScenarioError(null);
    setScenarioSummary(null);
    try {
      await resetSyntheticData();
      try {
        setUser(await getMe());
      } catch {
        // The reset succeeded; the next bootstrap will refresh the session.
      }
      profile.refresh();
      await load();
    } catch (caught) {
      setScenarioError(isApiError(caught) ? caught.message : '重置失败');
    } finally {
      setScenarioBusy(null);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial fetch
    if (mode === 'api') void load();
    else setLoading(false);
  }, [mode]);

  if (mode === 'mock') {
    return (
      <View style={styles.page}>
        <EmptyState
          title="开发页面只在真实后端模式可用"
          body="当前是演示模式，没有模型运行时数据。把 EXPO_PUBLIC_DATA_SOURCE 设为 api 并连接后端后再看。"
        />
      </View>
    );
  }

  if (loading) {
    return (
      <View style={styles.page}>
        <LoadingState label="正在读取模型运行时…" />
      </View>
    );
  }

  if (error || !data) {
    return (
      <View style={styles.page}>
        <ErrorState
          title="模型运行时读取失败"
          body={error ?? '没有返回数据。'}
          onRetry={() => void load()}
        />
      </View>
    );
  }

  const shadow = data.shadow_summary;
  return (
    <View style={styles.page}>
      <View style={styles.head}>
        <View style={styles.headText}>
          <Text style={[styles.title, { color: colors.ink }]}>模型运行时</Text>
          <Text style={[styles.body, { color: colors.inkMuted }]}>
            开发与比赛演示用。Level 3 目前只在 shadow 模式运行，不参与用户的生产计划决策。
          </Text>
        </View>
        <Button label="刷新" variant="tonal" size="sm" icon="refresh" onPress={() => void load()} />
      </View>

      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <Text style={[styles.cardTitle, { color: colors.ink }]}>Level 3 模式</Text>
          <View style={styles.facts}>
            <Fact label="请求模式" value={data.requested_mode} />
            <Fact label="生效模式" value={data.effective_mode} />
            <Fact label="原因" value={data.mode_reason ?? '—'} />
          </View>
        </View>
      </Surface>

      <View style={styles.grid}>
        {data.layers.map((layer) => (
          <Surface key={layer.level} level="level1" radius="lg" style={styles.layerCard}>
            <View style={styles.card}>
              <View style={styles.layerHead}>
                <Text style={[styles.cardTitle, { color: colors.ink }]}>
                  {LEVEL_LABEL[layer.level] ?? layer.level}
                </Text>
                <Text
                  style={[
                    styles.badge,
                    {
                      color: layer.status === 'ok' ? colors.primary : colors.warning,
                      borderColor: layer.status === 'ok' ? colors.primary : colors.warning,
                    },
                  ]}>
                  {STATUS_LABEL[layer.status] ?? layer.status}
                </Text>
              </View>
              <Fact label="模型版本" value={layer.model_version} mono />
              <Fact label="artifact 版本" value={layer.artifact_version || '—'} mono />
              <Fact label="feature 版本" value={layer.feature_version || '—'} mono />
              <Fact label="artifact hash" value={layer.artifact_hash || '—'} mono />
              {layer.mode ? <Fact label="模式" value={layer.mode} /> : null}
              {layer.degraded_reason ? (
                <Text style={[styles.note, { color: colors.inkFaint }]}>
                  降级原因：{layer.degraded_reason}
                </Text>
              ) : null}
            </View>
          </Surface>
        ))}
      </View>

      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <Text style={[styles.cardTitle, { color: colors.ink }]}>Level 3 Shadow</Text>
          {shadow.status === 'no_runtime_data' ? (
            <Text style={[styles.body, { color: colors.inkMuted }]}>
              还没有运行数据。生成并确认计划后，shadow 推理会写入审计表；这里会显示 runs / success rate / disagreement。
            </Text>
          ) : (
            <View style={styles.facts}>
              <Fact label="runs" value={String(shadow.runs)} mono />
              <Fact
                label="success rate"
                value={shadow.success_rate == null ? '—' : `${Math.round(shadow.success_rate * 100)}%`}
                mono
              />
              <Fact label="failures" value={String(shadow.failures)} mono />
              <Fact
                label="mean disagreement"
                value={
                  shadow.mean_disagreement == null
                    ? '—'
                    : shadow.mean_disagreement.toFixed(3)
                }
                mono
              />
            </View>
          )}
        </View>
      </Surface>

      {syntheticEnabled ? (
        <Surface level="level1" radius="lg">
          <View style={styles.card}>
            <Text style={[styles.cardTitle, { color: colors.ink }]}>
              Synthetic Scenarios
            </Text>
            <Text style={[styles.body, { color: colors.inkMuted }]}>
              Synthetic / 演示数据。导入的是任务、执行和反馈观测，不会直接写入 Level 2/3
              输出；模型状态与 shadow 预测仍由真实 runtime 计算。不得用于真实模型准确率声明。
            </Text>
            {syntheticStatus?.synthetic_present ? (
              <Text style={[styles.note, { color: colors.warning }]}>
                当前账号包含 synthetic 观测：
                {Object.entries(syntheticStatus.counts)
                  .map(([key, value]) => `${key}=${value}`)
                  .join(' · ')}
              </Text>
            ) : (
              <Text style={[styles.note, { color: colors.inkMuted }]}>
                当前账号没有 synthetic 数据。
              </Text>
            )}
            {scenarioError ? (
              <InlineNotice message={scenarioError} onDismiss={() => setScenarioError(null)} />
            ) : null}
            {scenarioSummary ? (
              <View style={styles.scenarioSummary}>
                <Text style={[styles.note, { color: colors.ink }]}>
                  已导入 {scenarioSummary.scenario}：{scenarioSummary.days_imported} 天 ·{' '}
                  {scenarioSummary.tasks_imported} 任务 · {scenarioSummary.feedback_imported} 反馈
                </Text>
                <Text style={[styles.note, { color: colors.inkMuted }]}>
                  Level 1 {scenarioSummary.level1_status} · Level 2 {scenarioSummary.level2_status}
                  {scenarioSummary.level2_observed_on
                    ? `（${scenarioSummary.level2_observed_on}）`
                    : ''}{' '}
                  · shadow {scenarioSummary.shadow_runs_before} → {scenarioSummary.shadow_runs_after}
                </Text>
                {scenarioSummary.warnings.map((warning) => (
                  <Text key={warning} style={[styles.note, { color: colors.inkFaint }]}>
                    {warning}
                  </Text>
                ))}
              </View>
            ) : null}
            {showcaseLocked ? (
              <Text style={[styles.note, { color: colors.warning }]}>
                受保护的展示账号：Synthetic 导入/重置已禁用。需要重建时运行
                scripts/seed_showcase_account.py。
              </Text>
            ) : null}
            <View style={styles.scenarioGrid}>
              {scenarios.map((scenario) => (
                <Button
                  key={scenario.name}
                  label={
                    scenarioBusy === scenario.name ? `导入中… ${scenario.name}` : scenario.name
                  }
                  variant="tonal"
                  size="sm"
                  disabled={scenarioBusy != null || showcaseLocked}
                  onPress={() => void importScenario(scenario.name)}
                />
              ))}
            </View>
            <View style={styles.scenarioFooter}>
              <Button
                label={scenarioBusy === 'reset' ? '重置中…' : '重置 synthetic 数据'}
                variant="outlined"
                size="sm"
                disabled={scenarioBusy != null || showcaseLocked}
                onPress={() => void resetSynthetic()}
              />
              <Text style={[styles.note, { color: colors.inkFaint }]}>
                只删除当前账号的 synthetic 数据，真实数据与其他用户不受影响。
              </Text>
            </View>
          </View>
        </Surface>
      ) : null}
    </View>
  );
}

function Fact({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  const { colors } = useTheme();
  return (
    <View style={styles.fact}>
      <Text style={[styles.factLabel, { color: colors.inkFaint }]}>{label}</Text>
      <Text
        numberOfLines={1}
        style={[styles.factValue, mono && styles.mono, { color: colors.ink }]}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { gap: Space.xl },
  head: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  headText: { flexGrow: 1, flexBasis: 320, gap: Space.xs },
  title: { fontSize: Type.headlineSmall, fontWeight: '600' },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 680,
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: Space.md },
  layerCard: { flexGrow: 1, flexBasis: 300, minWidth: 260 },
  card: { padding: Space.lg, gap: Space.sm },
  cardTitle: { fontSize: Type.titleMedium, fontWeight: '600' },
  layerHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.sm,
  },
  badge: {
    borderWidth: 1,
    borderRadius: Radius.pill,
    paddingHorizontal: Space.sm,
    paddingVertical: 2,
    fontSize: Type.labelSmall,
    overflow: 'hidden',
  },
  facts: { gap: Space.xs },
  fact: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  factLabel: { fontSize: Type.labelMedium, flexShrink: 0 },
  factValue: { fontSize: Type.bodyMedium, flexShrink: 1, textAlign: 'right' },
  mono: { fontFamily: Fonts.mono, fontSize: Type.labelSmall },
  note: { fontSize: Type.labelSmall, lineHeight: Type.labelSmall * Line.normal },
  scenarioSummary: { gap: Space.xs, paddingTop: Space.xs },
  scenarioGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Space.sm },
  scenarioFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: Space.md,
  },
});