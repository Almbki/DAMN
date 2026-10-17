import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { InlineNotice, SaveStatus, type SaveState } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { PREFERENCE_BOUNDS, clampPreference } from '@/domain/preferences';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

type PreferenceKey = 'dailyLimitMinutes' | 'bufferMinutes' | 'highCognitiveMaxPerDay';

export default function SettingsScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const {
    user,
    mode,
    preferences,
    updatePreferences,
    updateWeight,
    actionError,
    clearActionError,
  } = usePlan();

  const [saveState, setSaveState] = useState<SaveState>('idle');
  const prefsRef = useRef(preferences);
  const weightRef = useRef(user.execution_weight);
  const actionErrorRef = useRef(actionError);
  const pendingSavesRef = useRef(0);
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep the steppers on the latest provider value, while a save is in flight
  // they keep the optimistic value written below.
  useEffect(() => {
    if (saveState === 'saving') return;
    prefsRef.current = preferences;
  }, [preferences, saveState]);

  useEffect(() => {
    if (saveState === 'saving') return;
    weightRef.current = user.execution_weight;
  }, [user.execution_weight, saveState]);

  useEffect(() => {
    actionErrorRef.current = actionError;
  }, [actionError]);

  useEffect(
    () => () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    },
    [],
  );

  const runSave = async (run: () => Promise<void>) => {
    pendingSavesRef.current += 1;
    setSaveState('saving');
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current);
      idleTimerRef.current = null;
    }
    try {
      await run();
      // Let the provider's actionError land before deciding success/failure.
      await new Promise((resolve) => setTimeout(resolve, 40));
      if (actionErrorRef.current) {
        setSaveState('error');
      } else if (pendingSavesRef.current === 1) {
        setSaveState('saved');
        idleTimerRef.current = setTimeout(() => setSaveState('idle'), 2200);
      }
    } catch {
      setSaveState('error');
    } finally {
      pendingSavesRef.current -= 1;
    }
  };

  const shiftPreference = (key: PreferenceKey, delta: number) => {
    const current = prefsRef.current[key];
    const next = clampPreference(key, current + delta);
    if (next === current) return;
    prefsRef.current = { ...prefsRef.current, [key]: next };
    const patch =
      key === 'dailyLimitMinutes'
        ? { dailyLimitMinutes: next }
        : key === 'bufferMinutes'
          ? { bufferMinutes: next }
          : { highCognitiveMaxPerDay: next };
    void runSave(() => updatePreferences(patch));
  };

  const weightStep = (delta: number) => {
    const current = weightRef.current;
    const next = Math.round(Math.min(1, Math.max(0, current + delta)) * 100) / 100;
    if (next === current) return;
    weightRef.current = next;
    void runSave(() => updateWeight(next));
  };

  const saveError = saveState === 'error' ? (actionError ?? '保存失败，请稍后重试。') : null;

  return (
    <View style={styles.page}>
      <View style={styles.statusRow}>
        <Text style={[styles.statusText, { color: colors.inkMuted }]}>
          这些设置会自动保存，并在下次生成计划时生效。
        </Text>
        <SaveStatus state={saveState} />
      </View>

      {saveError || actionError ? (
        <InlineNotice
          message={saveError ?? actionError ?? ''}
          onDismiss={() => {
            clearActionError();
            setSaveState('idle');
          }}
        />
      ) : null}

      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <Text style={[styles.title, { color: colors.ink }]}>账号信息</Text>
          <View style={styles.fact}>
            <Text style={[styles.factLabel, { color: colors.inkMuted }]}>邮箱</Text>
            <Text style={[styles.factValue, { color: colors.ink }]}>{user.email}</Text>
          </View>
          <View style={styles.fact}>
            <Text style={[styles.factLabel, { color: colors.inkMuted }]}>昵称</Text>
            <Text style={[styles.factValue, { color: colors.ink }]}>
              {user.display_name ?? '—'}
            </Text>
          </View>
          <View style={styles.fact}>
            <Text style={[styles.factLabel, { color: colors.inkMuted }]}>数据来源</Text>
            <View style={styles.sourceRow}>
              <Text style={[styles.factValue, { color: colors.ink }]}>
                {mode === 'api' ? '真实后端' : '演示模式'}
              </Text>
              {mode === 'mock' ? (
                <View style={[styles.demoBadge, { backgroundColor: colors.warningContainer }]}>
                  <Text style={[styles.demoText, { color: colors.onWarningContainer }]}>DEMO</Text>
                </View>
              ) : null}
            </View>
          </View>
          <View style={styles.fact}>
            <Text style={[styles.factLabel, { color: colors.inkMuted }]}>执行权重</Text>
            <View style={styles.weightRow}>
              {mode === 'api' ? (
                <Step label="−" onPress={() => weightStep(-0.05)} />
              ) : null}
              <Text style={[styles.factValue, styles.mono, { color: colors.ink }]}>
                {user.execution_weight.toFixed(2)}
              </Text>
              {mode === 'api' ? <Step label="＋" onPress={() => weightStep(0.05)} /> : null}
            </View>
          </View>
          <Text style={[styles.helper, { color: colors.inkFaint }]}>
            {mode === 'api'
              ? '演示账号自动登录；执行权重会同步到后端。'
              : '演示模式：数据只保存在本机，不会写入后台。'}
          </Text>
        </View>
      </Surface>

      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <Text style={[styles.title, { color: colors.ink }]}>排程上限</Text>
          <Text style={[styles.body, { color: colors.inkMuted }]}>
            这里只负责生成计划时的硬上限：单日上限、任务之间的缓冲，以及每天最多几条高认知任务。
          </Text>

          <PrefRow
            label="单日上限"
            hint="一天最多排多久的活"
            value={preferences.dailyLimitMinutes}
            unit="分钟"
            onShift={(delta) => shiftPreference('dailyLimitMinutes', delta)}
            step={PREFERENCE_BOUNDS.dailyLimitMinutes.step}
          />
          <PrefRow
            label="缓冲时间"
            hint="任务之间留的空档"
            value={preferences.bufferMinutes}
            unit="分钟"
            onShift={(delta) => shiftPreference('bufferMinutes', delta)}
            step={PREFERENCE_BOUNDS.bufferMinutes.step}
          />
          <PrefRow
            label="高认知任务上限"
            hint="每天最多几条费脑子的任务"
            value={preferences.highCognitiveMaxPerDay}
            unit="条"
            onShift={(delta) => shiftPreference('highCognitiveMaxPerDay', delta)}
            step={PREFERENCE_BOUNDS.highCognitiveMaxPerDay.step}
          />

          <View style={[styles.crossLink, { borderTopColor: colors.outlineVariant }]}>
            <Text style={[styles.helper, { color: colors.inkMuted }]}>
              作息时间和每日可投入时间属于个人档案，在「基础档案」里设置。
            </Text>
            <Button
              label="去基础档案"
              variant="tonal"
              size="sm"
              icon="arrowRight"
              onPress={() => router.push('/profile-details')}
            />
          </View>
        </View>
      </Surface>
    </View>
  );
}

function PrefRow({
  label,
  hint,
  value,
  unit,
  step,
  onShift,
}: {
  label: string;
  hint: string;
  value: number;
  unit: string;
  step: number;
  onShift: (delta: number) => void;
}) {
  const { colors } = useTheme();
  return (
    <View style={[styles.prefRow, { borderTopColor: colors.outlineVariant }]}>
      <View style={styles.prefText}>
        <Text style={[styles.prefLabel, { color: colors.ink }]}>{label}</Text>
        <Text style={[styles.helper, { color: colors.inkMuted }]}>{hint}</Text>
      </View>
      <View style={styles.prefControl}>
        <Step label="−" onPress={() => onShift(-step)} />
        <Text style={[styles.prefValue, { color: colors.ink }]}>
          {value}
          <Text style={[styles.prefUnit, { color: colors.inkMuted }]}> {unit}</Text>
        </Text>
        <Step label="＋" onPress={() => onShift(step)} />
      </View>
    </View>
  );
}

function Step({ label, onPress }: { label: string; onPress: () => void }) {
  const { colors } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label === '−' ? '减少' : '增加'}
      onPress={onPress}
      style={[styles.step, { borderColor: colors.outline }]}>
      <Text style={[styles.stepText, { color: colors.primary }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: Space.xxl,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  statusText: {
    flexGrow: 1,
    flexBasis: 260,
    fontSize: Type.labelLarge,
    lineHeight: Type.labelLarge * Line.normal,
  },
  card: {
    padding: Space.xl,
    gap: Space.md,
  },
  title: {
    fontSize: Type.titleLarge,
    fontWeight: '600',
  },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 560,
  },
  fact: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.lg,
  },
  factLabel: {
    fontSize: Type.bodyMedium,
  },
  factValue: {
    fontSize: Type.bodyLarge,
  },
  sourceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  demoBadge: {
    borderRadius: Radius.pill,
    paddingHorizontal: Space.sm,
    paddingVertical: 2,
  },
  demoText: {
    fontSize: Type.labelSmall,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  mono: {
    fontFamily: Fonts.mono,
  },
  weightRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  helper: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * 1.5,
    maxWidth: 560,
  },
  prefRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.md,
    borderTopWidth: 1,
    paddingTop: Space.md,
  },
  prefText: {
    flexGrow: 1,
    flexBasis: 220,
    gap: 2,
  },
  prefLabel: {
    fontSize: Type.bodyLarge,
  },
  prefControl: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  prefValue: {
    fontFamily: Fonts.mono,
    fontSize: Type.titleMedium,
    minWidth: 96,
    textAlign: 'center',
  },
  prefUnit: {
    fontSize: Type.labelMedium,
  },
  step: {
    width: 44,
    height: 44,
    borderWidth: 1,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepText: {
    fontSize: Type.bodyLg,
    fontWeight: '600',
  },
  crossLink: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.md,
    borderTopWidth: 1,
    paddingTop: Space.lg,
    marginTop: Space.xs,
  },
});
