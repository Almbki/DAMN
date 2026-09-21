import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Surface } from '@/components/ui/surface';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { PREFERENCE_BOUNDS, clampPreference } from '@/domain/preferences';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

export default function SettingsScreen() {
  const { colors } = useTheme();
  const { user, mode, preferences, updatePreferences, updateWeight } = usePlan();

  const weightStep = (delta: number) => {
    const next = Math.round(Math.min(1, Math.max(0, user.execution_weight + delta)) * 100) / 100;
    if (next !== user.execution_weight) void updateWeight(next);
  };

  return (
    <View style={styles.page}>
      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <Text style={[styles.title, { color: colors.ink }]}>账号信息</Text>
          <View style={styles.fact}>
            <Text style={[styles.factLabel, { color: colors.inkMuted }]}>邮箱</Text>
            <Text style={[styles.factValue, { color: colors.ink }]}>{user.email}</Text>
          </View>
          <View style={styles.fact}>
            <Text style={[styles.factLabel, { color: colors.inkMuted }]}>昵称</Text>
            <Text style={[styles.factValue, { color: colors.ink }]}>{user.display_name ?? '—'}</Text>
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
            {mode === 'api' ? '执行权重会同步到后端。' : '演示模式：权重只影响本机判断。'}
          </Text>
        </View>
      </Surface>

      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <Text style={[styles.title, { color: colors.ink }]}>排程偏好</Text>
          <Text style={[styles.body, { color: colors.inkMuted }]}>
            这里设一次就会一直生效，之后每次生成计划都会自动带上，不用重填。
          </Text>

          <PrefRow
            label="每日可投入时间"
            hint="每天执行计划的时长上限"
            value={preferences.availableMinutesPerDay}
            unit="分钟"
            onShift={(delta) =>
              void updatePreferences({
                availableMinutesPerDay: clampPreference(
                  'availableMinutesPerDay',
                  preferences.availableMinutesPerDay + delta,
                ),
              })
            }
            step={PREFERENCE_BOUNDS.availableMinutesPerDay.step}
          />
          <PrefRow
            label="单日上限"
            hint="一天最多排多久的活"
            value={preferences.dailyLimitMinutes}
            unit="分钟"
            onShift={(delta) =>
              void updatePreferences({
                dailyLimitMinutes: clampPreference(
                  'dailyLimitMinutes',
                  preferences.dailyLimitMinutes + delta,
                ),
              })
            }
            step={PREFERENCE_BOUNDS.dailyLimitMinutes.step}
          />
          <PrefRow
            label="缓冲时间"
            hint="任务之间留的空档"
            value={preferences.bufferMinutes}
            unit="分钟"
            onShift={(delta) =>
              void updatePreferences({
                bufferMinutes: clampPreference('bufferMinutes', preferences.bufferMinutes + delta),
              })
            }
            step={PREFERENCE_BOUNDS.bufferMinutes.step}
          />
          <PrefRow
            label="高认知任务上限"
            hint="每天最多几条费脑子的任务"
            value={preferences.highCognitiveMaxPerDay}
            unit="条"
            onShift={(delta) =>
              void updatePreferences({
                highCognitiveMaxPerDay: clampPreference(
                  'highCognitiveMaxPerDay',
                  preferences.highCognitiveMaxPerDay + delta,
                ),
              })
            }
            step={PREFERENCE_BOUNDS.highCognitiveMaxPerDay.step}
          />

          <Text style={[styles.helper, { color: colors.inkFaint }]}>
            作息与入睡/起床时间在「画像 · 基础档案」里设置。
          </Text>
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
    width: 40,
    height: 40,
    borderWidth: 1,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepText: {
    fontSize: Type.bodyLg,
    fontWeight: '600',
  },
});
