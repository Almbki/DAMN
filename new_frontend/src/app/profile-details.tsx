import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { Surface } from '@/components/ui/surface';
import { TextField } from '@/components/ui/text-field';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import { PREFERENCE_BOUNDS, clampPreference } from '@/domain/preferences';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

const TIME_RE = /^([01]\d|2[0-3]):([0-5]\d)$/;

function sleepHours(start: string, end: string): number | null {
  if (!TIME_RE.test(start) || !TIME_RE.test(end)) return null;
  const [sh, sm] = start.split(':').map(Number);
  const [eh, em] = end.split(':').map(Number);
  const minutes = (eh * 60 + em - (sh * 60 + sm) + 1440) % 1440;
  return Math.round((minutes / 60) * 10) / 10;
}

export default function ProfileDetailsScreen() {
  const { colors } = useTheme();
  const { preferences, updatePreferences } = usePlan();
  const [start, setStart] = useState(preferences.sleepStart);
  const [end, setEnd] = useState(preferences.sleepEnd);

  const hours = sleepHours(start, end);
  const step = PREFERENCE_BOUNDS.availableMinutesPerDay.step;

  function commitSleep(nextStart: string, nextEnd: string) {
    setStart(nextStart);
    setEnd(nextEnd);
    if (TIME_RE.test(nextStart) && TIME_RE.test(nextEnd)) {
      void updatePreferences({ sleepStart: nextStart, sleepEnd: nextEnd });
    }
  }

  function shiftAvailable(delta: number) {
    void updatePreferences({
      availableMinutesPerDay: clampPreference(
        'availableMinutesPerDay',
        preferences.availableMinutesPerDay + delta,
      ),
    });
  }

  return (
    <View style={styles.page}>
      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <Text style={[styles.title, { color: colors.ink }]}>作息</Text>
          <Text style={[styles.body, { color: colors.inkMuted }]}>
            用来避免把任务排到你睡觉的时间。改一次会一直生效。
          </Text>
          <View style={styles.times}>
            <View style={styles.timeField}>
              <TextField
                label="入睡"
                value={start}
                onChangeText={(value) => commitSleep(value, end)}
                placeholder="23:30"
                testID="sleep-start"
                background={colors.surfaceContainerLowest}
              />
            </View>
            <View style={styles.timeField}>
              <TextField
                label="起床"
                value={end}
                onChangeText={(value) => commitSleep(start, value)}
                placeholder="07:30"
                testID="sleep-end"
                background={colors.surfaceContainerLowest}
              />
            </View>
          </View>
          <Text style={[styles.helper, { color: colors.inkMuted }]}>
            {hours == null
              ? '时间格式用 HH:MM，例如 23:30。'
              : `大约 ${hours} 小时睡眠。`}
          </Text>
        </View>
      </Surface>

      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <Text style={[styles.title, { color: colors.ink }]}>每日可投入时间</Text>
          <Text style={[styles.body, { color: colors.inkMuted }]}>
            你每天愿意拿来执行计划的总时长上限。
          </Text>
          <View style={styles.stepperRow}>
            <Button label="−" variant="outlined" size="sm" onPress={() => shiftAvailable(-step)} />
            <Text style={[styles.value, { color: colors.ink }]}>
              {preferences.availableMinutesPerDay}
              <Text style={[styles.valueUnit, { color: colors.inkMuted }]}> 分钟</Text>
            </Text>
            <Button label="＋" variant="outlined" size="sm" onPress={() => shiftAvailable(step)} />
          </View>
        </View>
      </Surface>

      <Text style={[styles.footer, { color: colors.inkFaint }]}>
        单日上限、缓冲和高认知上限属于排程策略，在「设置」里调整。
      </Text>
    </View>
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
  times: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  timeField: {
    flexGrow: 1,
    flexBasis: 160,
    maxWidth: 220,
  },
  helper: {
    fontSize: Type.labelMedium,
  },
  stepperRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.lg,
  },
  value: {
    fontFamily: Fonts.mono,
    fontSize: Type.titleLarge,
  },
  valueUnit: {
    fontSize: Type.labelLarge,
  },
  footer: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
});
