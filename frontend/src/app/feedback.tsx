import { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { Line, Radius, Space, Type } from '@/constants/tokens';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

export default function FeedbackScreen() {
  const { colors } = useTheme();
  const { completedCount, totalCount } = usePlan();
  const [summary, setSummary] = useState('');
  const [reason, setReason] = useState('');
  const [plan, setPlan] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const rate = totalCount === 0 ? 0 : completedCount / totalCount;

  return (
    <View style={styles.page}>
      <View style={[styles.card, { borderColor: colors.line }]}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>每日反馈</Text>
        <Text style={[styles.cardBody, { color: colors.inkMuted }]}>
          完成率低于一半时，我会给你排一张更轻的计划，而不是催你补上。
        </Text>

        <Field label="今天完成了什么" value={summary} onChange={setSummary} placeholder="简述今天完成的任务…" />
        <Field label="没做完的原因" value={reason} onChange={setReason} placeholder="例如：被打断、预估时间不足…" />
        <Field label="明天想怎么调整" value={plan} onChange={setPlan} placeholder="例如：减少任务量、换个时间段…" />

        <Button
          label={submitted ? '已提交' : '提交反馈'}
          variant="primary"
          onPress={() => setSubmitted(true)}
        />
        {submitted ? (
          <Text style={[styles.helper, { color: colors.mintInk }]}>
            已提交。如果完成率低于一半，会生成新一版计划并在这里告诉你。
          </Text>
        ) : null}
      </View>

      <View style={[styles.card, { borderColor: colors.line }]}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>上周回顾</Text>
        <View style={styles.bigRow}>
          <Text style={[styles.big, { color: colors.ink }]}>{completedCount}</Text>
          <Text style={[styles.bigDen, { color: colors.inkMuted }]}>/ {totalCount}</Text>
          <Text style={[styles.bigNote, { color: colors.inkMuted }]}>
            上周完成 <Text style={styles.mono}>{Math.round(rate * 100)}%</Text>，这周按相近的量安排
          </Text>
        </View>

        <View style={styles.bars}>
          <Bar label="上周安排" value={5} max={6} />
          <Bar label="上周完成" value={completedCount} max={Math.max(totalCount, 1)} />
          <Bar label="本周安排" value={totalCount} max={Math.max(totalCount, 5)} />
        </View>

        <Button label="还是按原来的量来吧" variant="secondary" onPress={() => undefined} />
      </View>
    </View>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  const { colors } = useTheme();
  const [focused, setFocused] = useState(false);
  return (
    <View style={styles.field}>
      <Text style={[styles.fieldLabel, { color: colors.inkMuted }]}>{label}</Text>
      <TextInput
        multiline
        value={value}
        onChangeText={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        placeholderTextColor={colors.inkFaint}
        accessibilityLabel={label}
        style={[
          styles.textarea,
          {
            color: colors.ink,
            borderColor: focused ? colors.lineStrong : colors.line,
            backgroundColor: colors.paper,
          },
        ]}
      />
    </View>
  );
}

function Bar({ label, value, max }: { label: string; value: number; max: number }) {
  const { colors } = useTheme();
  const pct = max === 0 ? 0 : Math.min(1, value / max);
  return (
    <View style={styles.barRow}>
      <Text style={[styles.barLabel, { color: colors.inkMuted }]}>{label}</Text>
      <View style={[styles.barTrack, { backgroundColor: colors.line }]}>
        <View
          style={[styles.barFill, { backgroundColor: colors.ink, width: `${pct * 100}%` }]}
        />
      </View>
      <Text style={[styles.barValue, { color: colors.ink }]}>{value}</Text>
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
  field: {
    gap: Space.sm,
  },
  fieldLabel: {
    fontSize: Type.small,
  },
  textarea: {
    minHeight: 84,
    borderWidth: 1,
    borderRadius: Radius.sm,
    padding: Space.md,
    fontSize: Type.body,
    textAlignVertical: 'top',
  },
  helper: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.relaxed,
  },
  bigRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: Space.sm,
    flexWrap: 'wrap',
  },
  big: {
    fontSize: Type.displaySm,
    lineHeight: Type.displaySm * 0.95,
    fontFamily: 'IBMPlexMono_500Medium',
  },
  bigDen: {
    fontSize: Type.heading,
    fontFamily: 'IBMPlexMono_400Regular',
  },
  bigNote: {
    fontSize: Type.body,
    flexShrink: 1,
  },
  mono: {
    fontFamily: 'IBMPlexMono_500Medium',
  },
  bars: {
    gap: Space.md,
  },
  barRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
  },
  barLabel: {
    width: 68,
    fontSize: Type.small,
  },
  barTrack: {
    flex: 1,
    height: 10,
    borderRadius: Radius.sm,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: Radius.sm,
  },
  barValue: {
    width: 24,
    textAlign: 'right',
    fontSize: Type.small,
    fontFamily: 'IBMPlexMono_400Regular',
  },
});
