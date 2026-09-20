import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { describeApiError } from '@/api/client';
import * as endpoints from '@/api/endpoints';
import { formatDateTimeLabel, formatDuration } from '@/api/format';
import type { InsightRead } from '@/api/types';
import { Card, MonoRule, MonoText, Screen, Tag } from '@/components/mono';
import { MonoSpace } from '@/constants/mono';
import { usePlan } from '@/plan/plan-provider';
import { useAuthToken, useSession } from '@/session/session-provider';

/**
 * 用户画像。
 *
 * 数据来自两处，都是真接口：
 * - `GET /users/me` —— 账号资料（称呼 / 执行权重 / profile 标签）；
 * - `GET /plans/{id}/insights` —— 当前计划的完成率、计划用时 vs 实际用时、后端建议。
 *
 * 模板里的静态标签换成 `profile` 里的真实条目；没有就不显示，不编造。
 */
export default function ProfileScreen() {
  const token = useAuthToken();
  const { user } = useSession();
  const { plan, loadState } = usePlan();

  const [insight, setInsight] = useState<InsightRead | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const planId = plan?.id ?? null;

  useEffect(() => {
    let cancelled = false;

    (async () => {
      if (planId === null) {
        setInsight(null);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const result = await endpoints.getInsights(token, planId);
        if (!cancelled) setInsight(result);
      } catch (cause) {
        if (!cancelled) setError(describeApiError(cause));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [planId, token]);

  const profileEntries = user?.profile ? Object.entries(user.profile) : [];

  return (
    <Screen>
      <Card title="用户画像分析">
        <MonoText type="sub" color="sub">
          账号资料与后端基于历史数据生成的特征。
        </MonoText>
        <View>
          <Row label="邮箱" value={user?.email ?? '—'} />
          <MonoRule />
          <Row label="称呼" value={user?.display_name || '没填'} />
          <MonoRule />
          <Row
            label="执行权重"
            value={user ? `${Math.round(user.execution_weight * 100)}%（估时折扣）` : '—'}
          />
          <MonoRule />
          <Row label="注册时间" value={formatDateTimeLabel(user?.created_at) || '—'} />
        </View>

        <View style={styles.tags}>
          <MonoText type="label" color="sub">
            画像标签
          </MonoText>
          {profileEntries.length > 0 ? (
            <View style={styles.tagList}>
              {profileEntries.map(([key, value]) => (
                <Tag key={key} label={`${key}：${String(value)}`} />
              ))}
            </View>
          ) : (
            <MonoText type="caption" color="faint">
              后端还没有生成画像标签。随着你完成任务、提交反馈，这里会慢慢长出来。
            </MonoText>
          )}
        </View>
      </Card>

      <Card title="完成情况">
        {loadState === 'loading' || loadState === 'idle' ? (
          <MonoText type="body" color="faint">
            正在读统计…
          </MonoText>
        ) : !plan ? (
          <MonoText type="body" color="sub">
            还没有计划。去 Todo 写个目标生成一份，做完几件再回来看这页。
          </MonoText>
        ) : error ? (
          <MonoText type="body" color="danger">
            {error}
          </MonoText>
        ) : loading && !insight ? (
          <MonoText type="body" color="faint">
            正在向后端要统计…
          </MonoText>
        ) : insight ? (
          <View style={styles.insight}>
            <View style={styles.bigRow}>
              <MonoText type="display">{insight.completed_tasks}</MonoText>
              <MonoText type="title" color="sub">
                {' '}
                / {insight.total_tasks}
              </MonoText>
            </View>
            <MonoText type="body" color="sub">
              {insight.total_tasks === 0
                ? '这份计划里还没有任务。'
                : `完成了 ${Math.round(insight.completion_rate * 100)}%，实际用了 ${formatDuration(
                    insight.total_actual_minutes,
                  )}${
                    insight.total_planned_minutes > 0
                      ? `，原计划 ${formatDuration(insight.total_planned_minutes)}`
                      : ''
                  }。`}
            </MonoText>

            {insight.recommendations.length > 0 ? (
              <View style={styles.recs}>
                {insight.recommendations.map((item) => (
                  <MonoText key={item} type="sub" color="sub">
                    · {RECOMMENDATION_ZH[item] ?? item}
                  </MonoText>
                ))}
              </View>
            ) : null}
          </View>
        ) : null}
      </Card>
    </Screen>
  );
}

/** 后端建议是英文原文，逐句对应翻译，翻不到就原样显示。 */
const RECOMMENDATION_ZH: Record<string, string> = {
  'Completion rate is low - consider reducing daily load or replanning.':
    '完成率偏低，可以考虑减少每天的量，或者重排一次。',
  'Tasks finish faster than planned - the duration factor can be lowered.':
    '任务比预计完成得快，说明时长系数可以往下降一点。',
};

/** 一行「字段 → 值」，值右对齐。 */
function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <MonoText type="sub" color="sub">
        {label}
      </MonoText>
      <MonoText type="sub" style={styles.rowValue} numberOfLines={2}>
        {value}
      </MonoText>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: MonoSpace.four,
    minHeight: 36,
    paddingVertical: MonoSpace.two,
  },
  rowValue: { flexShrink: 1, flexGrow: 1, textAlign: 'right' },
  tags: { gap: MonoSpace.three },
  tagList: { gap: MonoSpace.two, alignItems: 'flex-start' },
  insight: { gap: MonoSpace.three },
  bigRow: { flexDirection: 'row', alignItems: 'baseline', gap: MonoSpace.one },
  recs: { gap: MonoSpace.one },
});
