import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { TextField } from '@/components/ui/text-field';
import { Line, Radius, Space, Type } from '@/constants/tokens';
import { parseISO } from '@/domain/date';
import { usePlan } from '@/state/plan';
import type { FeedbackResult } from '@/state/plan-context';
import { useTheme } from '@/state/theme';

const WEEKDAY = ['日', '一', '二', '三', '四', '五', '六'];

export default function FeedbackScreen() {
  const { colors } = useTheme();
  const { stats, submitFeedback } = usePlan();
  const [summary, setSummary] = useState('');
  const [reason, setReason] = useState('');
  const [plan, setPlan] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<FeedbackResult | null>(null);

  const weekMax = Math.max(1, ...stats.weekly.map((bucket) => bucket.count));
  const monthMax = Math.max(1, ...stats.monthly.map((bucket) => bucket.count));

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const response = await submitFeedback({
        completionRate: stats.rate,
        freeText: [summary, plan].filter(Boolean).join(' / '),
        delayReason: reason || undefined,
      });
      setResult(response);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <View style={styles.page}>
      <View style={[styles.card, { borderColor: colors.line }]}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>每日反馈</Text>
        <Text style={[styles.cardBody, { color: colors.inkMuted }]}>
          完成率低于一半时，我会给你排一张更轻的计划，而不是催你补上。
        </Text>

        <TextField label="今天完成了什么" value={summary} onChangeText={setSummary} placeholder="简述今天完成的任务…" />
        <TextField label="没做完的原因" value={reason} onChangeText={setReason} placeholder="例如：被打断、预估时间不足…" />
        <TextField label="明天想怎么调整" value={plan} onChangeText={setPlan} placeholder="例如：减少任务量、换个时间段…" />

        <Button
          label={submitting ? '提交中…' : result ? '已提交' : '提交反馈'}
          variant="primary"
          onPress={handleSubmit}
          disabled={submitting}
        />
        {result ? (
          <Text style={[styles.helper, { color: colors.mintInk }]}>
            {result.replanTriggered
              ? '已根据这次反馈生成新一版计划，任务已切到新版本。'
              : result.cooldownMessage ?? '已提交。完成率低于一半时会生成新一版计划。'}
          </Text>
        ) : null}
      </View>

      <View style={[styles.card, { borderColor: colors.line }]}>
        <Text style={[styles.cardTitle, { color: colors.ink }]}>统计与回顾</Text>

        <View style={styles.statRow}>
          <Stat label="已完成的待办" value={String(stats.doneCount)} />
          <Stat label="完成率" value={`${Math.round(stats.rate * 100)}%`} />
          <Stat label="连续完成" value={`${stats.streak} 天`} />
          <Stat label="最长连续" value={`${stats.longest} 天`} />
        </View>

        <View style={styles.block}>
          <Text style={[styles.blockTitle, { color: colors.inkMuted }]}>最近 7 天完成数</Text>
          <View style={styles.bars}>
            {stats.weekly.map((bucket) => (
              <Bar
                key={bucket.date}
                label={WEEKDAY[parseISO(bucket.date).getDay()]}
                value={bucket.count}
                max={weekMax}
              />
            ))}
          </View>
        </View>

        <View style={styles.block}>
          <Text style={[styles.blockTitle, { color: colors.inkMuted }]}>最近 6 个月完成数</Text>
          <View style={styles.bars}>
            {stats.monthly.map((bucket) => (
              <Bar
                key={bucket.date}
                label={bucket.date.slice(5)}
                value={bucket.count}
                max={monthMax}
              />
            ))}
          </View>
        </View>

        <View style={styles.focusRow}>
          <Text style={[styles.helper, { color: colors.inkMuted }]}>
            今日专注 <Text style={styles.mono}>{stats.focusToday}</Text> 分钟 · 本周专注{' '}
            <Text style={styles.mono}>{stats.focusWeek}</Text> 分钟
          </Text>
        </View>

        <Button label="还是按原来的量来吧" variant="secondary" onPress={() => undefined} />
      </View>
    </View>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.stat}>
      <Text style={[styles.statValue, { color: colors.ink }]}>{value}</Text>
      <Text style={[styles.statLabel, { color: colors.inkMuted }]}>{label}</Text>
    </View>
  );
}

function Bar({ label, value, max }: { label: string; value: number; max: number }) {
  const { colors } = useTheme();
  const ratio = max === 0 ? 0 : Math.min(1, value / max);
  return (
    <View style={styles.barCol}>
      <Text style={[styles.barValue, { color: colors.ink }]}>{value}</Text>
      <View style={[styles.barTrack, { backgroundColor: colors.line }]}>
        <View style={[styles.barFill, { backgroundColor: colors.ink, height: `${ratio * 100}%` }]} />
      </View>
      <Text style={[styles.barLabel, { color: colors.inkMuted }]}>{label}</Text>
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
  helper: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.relaxed,
  },
  mono: {
    fontFamily: 'IBMPlexMono_500Medium',
  },
  statRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.xxl,
  },
  stat: {
    gap: Space.xs,
  },
  statValue: {
    fontSize: Type.heading,
    fontFamily: 'IBMPlexMono_500Medium',
  },
  statLabel: {
    fontSize: Type.small,
  },
  block: {
    gap: Space.sm,
  },
  blockTitle: {
    fontSize: Type.small,
  },
  bars: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Space.sm,
    height: 96,
  },
  barCol: {
    flex: 1,
    alignItems: 'center',
    gap: Space.xs,
    height: '100%',
    justifyContent: 'flex-end',
  },
  barTrack: {
    width: '100%',
    flex: 1,
    borderRadius: Radius.sm,
    justifyContent: 'flex-end',
    overflow: 'hidden',
  },
  barFill: {
    width: '100%',
    borderRadius: Radius.sm,
  },
  barValue: {
    fontSize: Type.micro,
    fontFamily: 'IBMPlexMono_400Regular',
  },
  barLabel: {
    fontSize: Type.micro,
  },
  focusRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
});
