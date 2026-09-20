import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { Segmented } from '@/components/ui/segmented';
import { Line, Radius, Space, Type } from '@/constants/tokens';
import { usePlan } from '@/state/plan';
import { useTheme, type ThemeMode } from '@/state/theme';

const THEME_OPTIONS: { label: string; value: ThemeMode }[] = [
  { label: '浅色', value: 'light' },
  { label: '深色', value: 'dark' },
  { label: '跟系统', value: 'system' },
];

const MODELS = ['Agentic Modified v2', '标准模型'];
const FREQUENCY = ['每天提醒', '只在重要时提醒', '关闭提醒'];

export default function SettingsScreen() {
  const { colors, mode, setMode } = useTheme();
  const { user } = usePlan();
  const [model, setModel] = useState(0);
  const [frequency, setFrequency] = useState(0);

  return (
    <View style={styles.page}>
      <View style={[styles.card, { borderColor: colors.line }]}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>外观</Text>
        <Text style={[styles.cardBody, { color: colors.inkMuted }]}>
          默认浅色。选择会保存在本机，不影响其他设备。
        </Text>
        <View style={styles.row}>
          {THEME_OPTIONS.map((option) => {
            const selected = option.value === mode;
            return (
              <Pressable
                key={option.value}
                accessibilityRole="radio"
                accessibilityState={{ selected }}
                onPress={() => setMode(option.value)}
                style={[
                  styles.chip,
                  {
                    borderColor: selected ? colors.ink : colors.line,
                    backgroundColor: selected ? colors.ink : 'transparent',
                  },
                ]}>
                <Text style={[styles.chipText, { color: selected ? colors.onInk : colors.ink }]}>
                  {option.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <View style={[styles.card, { borderColor: colors.line }]}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>安排</Text>
        <Segmented label="拆解模型" options={MODELS} value={model} onChange={setModel} />
        <Segmented
          label="提醒频率"
          options={FREQUENCY}
          value={frequency}
          onChange={setFrequency}
        />
        <Button label="保存设置" variant="primary" onPress={() => undefined} />
      </View>

      <View style={[styles.card, { borderColor: colors.line }]}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>账号</Text>
        <View style={styles.fact}>
          <Text style={[styles.factLabel, { color: colors.inkMuted }]}>邮箱</Text>
          <Text style={[styles.factValue, { color: colors.ink }]}>{user.email}</Text>
        </View>
        <Text style={[styles.helper, { color: colors.inkMuted }]}>
          登录与注册暂未接入，当前使用演示账号。
        </Text>
      </View>
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
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  chip: {
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.lg,
    minHeight: 40,
    justifyContent: 'center',
  },
  chipText: {
    fontSize: Type.body,
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
