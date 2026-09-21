import { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { Surface } from '@/components/surface';
import { Segmented } from '@/components/ui/segmented';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { usePlan } from '@/state/plan';
import { usePreferences } from '@/state/preferences';
import { useTheme } from '@/state/theme';

const THEME_OPTIONS = ['浅色', '深色', '跟系统'] as const;

export default function SettingsScreen() {
  const { colors, mode, setMode } = useTheme();
  const { user } = usePlan();
  const { preferences, setPreference } = usePreferences();

  const themeIndex = mode === 'light' ? 0 : mode === 'dark' ? 1 : 2;

  return (
    <View style={styles.page}>
      <Surface elevation="raised" radius={Radius.lg} style={styles.card}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>外观</Text>
        <Text style={[styles.hint, { color: colors.inkMuted }]}>
          顶栏不再放切换按钮，深浅色在这里设一次。
        </Text>
        <Segmented
          label="深浅色"
          options={THEME_OPTIONS}
          value={themeIndex}
          onChange={(index) => setMode(index === 0 ? 'light' : index === 1 ? 'dark' : 'system')}
        />
      </Surface>

      <Surface elevation="raised" radius={Radius.lg} style={styles.card}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>账号</Text>
        <Fact label="显示名" value={user.display_name ?? '—'} />
        <Fact label="邮箱" value={user.email} />
        <Fact label="执行权重" value={user.execution_weight.toFixed(2)} mono />
        <Text style={[styles.hint, { color: colors.inkMuted }]}>
          登录与注册暂未接入，当前使用演示账号。
        </Text>
      </Surface>

      <Surface elevation="raised" radius={Radius.lg} style={styles.card}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>排程偏好</Text>
        <Text style={[styles.hint, { color: colors.inkMuted }]}>
          设一次就一直生效，不用每次重填。改动离开输入框时即刻保存。
        </Text>

        <NumberField
          label="每日可投入时间"
          hint="一天最多排多少分钟"
          unit="分钟"
          value={preferences.dailyMinutes}
          min={30}
          max={720}
          onCommit={(value) => setPreference('dailyMinutes', value)}
        />
        <NumberField
          label="单日任务上限"
          hint="一天最多排几件"
          unit="件"
          value={preferences.dailyTaskCap}
          min={1}
          max={20}
          onCommit={(value) => setPreference('dailyTaskCap', value)}
        />
        <NumberField
          label="缓冲时间"
          hint="任务之间留多久"
          unit="分钟"
          value={preferences.bufferMinutes}
          min={0}
          max={120}
          onCommit={(value) => setPreference('bufferMinutes', value)}
        />
        <NumberField
          label="高认知任务上限"
          hint="一天最多几件费脑子的"
          unit="件"
          value={preferences.highLoadCap}
          min={0}
          max={10}
          onCommit={(value) => setPreference('highLoadCap', value)}
        />
      </Surface>
    </View>
  );
}

function Fact({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  const { colors } = useTheme();
  return (
    <View style={styles.fact}>
      <Text style={[styles.factLabel, { color: colors.inkMuted }]}>{label}</Text>
      <Text
        style={[styles.factValue, { color: colors.ink, fontFamily: mono ? Fonts.mono : undefined }]}>
        {value}
      </Text>
    </View>
  );
}

function NumberField({
  label,
  hint,
  unit,
  value,
  min,
  max,
  onCommit,
}: {
  label: string;
  hint: string;
  unit: string;
  value: number;
  min: number;
  max: number;
  onCommit: (value: number) => void;
}) {
  const { colors } = useTheme();
  const [text, setText] = useState(String(value));
  const [focused, setFocused] = useState(false);

  function commit() {
    setFocused(false);
    const parsed = Number.parseInt(text, 10);
    const next = Number.isFinite(parsed) ? Math.min(max, Math.max(min, parsed)) : value;
    setText(String(next));
    onCommit(next);
  }

  return (
    <View style={styles.field}>
      <View style={styles.fieldHead}>
        <Text style={[styles.fieldLabel, { color: colors.ink }]}>{label}</Text>
        <Text style={[styles.fieldHint, { color: colors.inkMuted }]}>{hint}</Text>
      </View>
      <View style={styles.inputRow}>
        <TextInput
          value={text}
          onChangeText={(raw) => setText(raw.replace(/[^0-9]/g, '').slice(0, 4))}
          onFocus={() => setFocused(true)}
          onBlur={commit}
          onSubmitEditing={commit}
          keyboardType="number-pad"
          accessibilityLabel={label}
          style={[
            styles.input,
            {
              color: colors.ink,
              borderColor: focused ? colors.accent : colors.line,
              backgroundColor: colors.paper,
            },
          ]}
        />
        <Text style={[styles.unit, { color: colors.inkMuted }]}>{unit}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: Space.xl,
  },
  card: {
    padding: Space.lg,
    gap: Space.lg,
  },
  cardTitle: {
    fontSize: Type.title,
    fontWeight: '700',
  },
  hint: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.relaxed,
  },
  fact: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.lg,
  },
  factLabel: {
    fontSize: Type.body,
  },
  factValue: {
    fontSize: Type.body,
  },
  field: {
    gap: Space.sm,
  },
  fieldHead: {
    gap: 2,
  },
  fieldLabel: {
    fontSize: Type.body,
    fontWeight: '700',
  },
  fieldHint: {
    fontSize: Type.small,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  input: {
    minHeight: 44,
    width: 96,
    borderWidth: 2,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.md,
    fontSize: Type.body,
    fontFamily: Fonts.mono,
  },
  unit: {
    fontSize: Type.small,
  },
});
