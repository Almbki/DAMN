import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Radius, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/** 0 = Monday … 6 = Sunday, matching the backend `recurrence_weekdays`. */
export const WEEKDAY_OPTIONS = [
  { value: 0, label: '一', name: '周一' },
  { value: 1, label: '二', name: '周二' },
  { value: 2, label: '三', name: '周三' },
  { value: 3, label: '四', name: '周四' },
  { value: 4, label: '五', name: '周五' },
  { value: 5, label: '六', name: '周六' },
  { value: 6, label: '日', name: '周日' },
] as const;

export const ALL_WEEKDAYS = WEEKDAY_OPTIONS.map((day) => day.value);
export const WEEKDAY_PRESETS = ['每天', '工作日', '周末', '自定义'] as const;

/** Preset index for a saved list; an empty list falls back to 每天. */
export function presetFromWeekdays(days: number[] | null | undefined): number {
  const sorted = Array.from(new Set(days ?? ALL_WEEKDAYS)).sort((a, b) => a - b);
  if (sorted.length === ALL_WEEKDAYS.length) return 0;
  if (sorted.join(',') === '0,1,2,3,4') return 1;
  if (sorted.join(',') === '5,6') return 2;
  return 3;
}

/** Short, human label for a saved list (used on the 待拆解 cards). */
export function weekdaysSummary(days: number[] | null | undefined): string {
  const preset = presetFromWeekdays(days);
  if (preset === 0) return '每天';
  if (preset === 1) return '工作日';
  if (preset === 2) return '周末';
  const selected = WEEKDAY_OPTIONS.filter((day) => (days ?? []).includes(day.value));
  return selected.length > 0 ? selected.map((day) => day.name).join('、') : '未选重复日';
}

export function daysForPreset(index: number): number[] | null {
  if (index === 0) return [...ALL_WEEKDAYS];
  if (index === 1) return [0, 1, 2, 3, 4];
  if (index === 2) return [5, 6];
  return null;
}

/** Seven explicit toggles: no hidden gestures, every day is its own target. */
export function WeekdayPicker({
  value,
  onChange,
  error,
}: {
  value: number[];
  onChange: (days: number[]) => void;
  error?: string | null;
}) {
  const { colors } = useTheme();

  function toggle(day: number) {
    if (value.includes(day)) {
      onChange(value.filter((item) => item !== day).sort((a, b) => a - b));
    } else {
      onChange([...value, day].sort((a, b) => a - b));
    }
  }

  return (
    <View style={styles.wrap}>
      <Text style={[styles.label, { color: colors.inkMuted }]}>重复日</Text>
      <View style={styles.row}>
        {WEEKDAY_OPTIONS.map((day) => {
          const selected = value.includes(day.value);
          return (
            <Pressable
              key={day.value}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              accessibilityLabel={day.name}
              onPress={() => toggle(day.value)}
              style={[
                styles.day,
                {
                  borderColor: selected ? colors.primary : colors.outline,
                  backgroundColor: selected ? colors.secondaryContainer : 'transparent',
                },
              ]}>
              <Text
                style={[
                  styles.dayText,
                  {
                    color: selected ? colors.onSecondaryContainer : colors.ink,
                    fontWeight: selected ? '600' : '400',
                  },
                ]}>
                {day.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
      {error ? <Text style={[styles.error, { color: colors.error }]}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: Space.sm,
  },
  label: {
    fontSize: Type.labelMedium,
  },
  row: {
    flexDirection: 'row',
    gap: Space.xs,
  },
  day: {
    flex: 1,
    minWidth: 36,
    minHeight: 44,
    borderWidth: 1,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dayText: {
    fontSize: Type.labelLarge,
  },
  error: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * 1.6,
  },
});
