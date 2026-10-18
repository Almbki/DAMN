import { StyleSheet, Text, View } from 'react-native';

import { Banner } from '@/components/task/banner';
import { Line, Space, Type } from '@/constants/tokens';
import type { FeedbackResult, FeedbackRoute } from '@/state/plan-context';
import { useTheme } from '@/state/theme';

const ROUTE_LABEL: Record<FeedbackRoute, string> = {
  none: '不重排',
  micro_adjust: '小幅调整',
  full_replan: '完整重排',
};

const ROUTE_REASON: Record<FeedbackRoute, string> = {
  none: '压力、精力和完成情况还没到需要重排的程度。',
  micro_adjust: '这次只做了小幅调整，没有替换整个计划。',
  full_replan: '这次没有生成新的计划版本。',
};

/**
 * Prefer the explicit `saved` flag. Older responses only carried
 * `cooldownMessage`, so keep the string fallback without making it the primary
 * path.
 */
export function feedbackSaved(result: FeedbackResult): boolean {
  if (typeof result.saved === 'boolean') return result.saved;
  if (result.replanTriggered) return true;
  if (result.cooldownMessage == null) return true;
  return result.cooldownMessage.startsWith('重排冷却中');
}

type Outcome = {
  tone: 'info' | 'success' | 'error';
  title: string;
  body: string;
};

function outcomeFor(result: FeedbackResult): Outcome {
  const saved = feedbackSaved(result);
  const replanned = result.mode === 'replanned' || result.replanTriggered;
  const replanError = result.replanError ?? null;

  if (!saved) {
    return {
      tone: 'error',
      title: '反馈未保存',
      body: replanError ?? result.cooldownMessage ?? '没有收到后端的确认，请稍后再试。',
    };
  }

  if (replanned) {
    return {
      tone: 'success',
      title: '已按反馈重排',
      body: `已生成新计划${result.replanPlanId != null ? `（#${result.replanPlanId}）` : ''}，去待办看看新的安排。`,
    };
  }

  if (replanError) {
    return {
      tone: 'info',
      title: '反馈已记录，重排未完成',
      body: `反馈已经保存，但重排没有完成：${replanError}`,
    };
  }

  const route = result.route ?? null;
  const reason = result.reasons?.[0] ?? (route ? ROUTE_REASON[route] : null);
  return {
    tone: 'info',
    title: '反馈已记录，本轮不重排',
    body: reason
      ? `反馈已经保存。${reason}`
      : '反馈已经保存，这次没有生成新的计划版本。',
  };
}

/**
 * The four submission outcomes: replanned / recorded / recorded with a failed
 * replan / not saved. Route and reasons stay visible when the backend returns
 * them.
 */
export function FeedbackResultBanner({
  result,
  onDismiss,
  onGoTodo,
}: {
  result: FeedbackResult;
  onDismiss: () => void;
  onGoTodo: () => void;
}) {
  const { colors } = useTheme();
  const outcome = outcomeFor(result);
  const saved = feedbackSaved(result);
  const replanned = result.mode === 'replanned' || result.replanTriggered;
  const route = result.route ?? null;
  const reasons = result.reasons ?? [];

  return (
    <View style={styles.wrap}>
      <Banner
        tone={outcome.tone}
        title={outcome.title}
        body={outcome.body}
        actionLabel={replanned ? '去待办' : undefined}
        onAction={replanned ? onGoTodo : undefined}
        onDismiss={onDismiss}
      />

      {saved && (route != null || reasons.length > 0) ? (
        <View style={styles.meta}>
          {route != null ? (
            <Text style={[styles.metaText, { color: colors.inkMuted }]}>
              调整策略：{ROUTE_LABEL[route]}
            </Text>
          ) : null}
          {reasons.slice(0, 4).map((reason, index) => (
            <Text
              key={`${index}-${reason}`}
              style={[styles.metaText, { color: colors.inkMuted }]}>
              · {reason}
            </Text>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: Space.sm,
  },
  meta: {
    gap: 2,
    paddingHorizontal: Space.xs,
  },
  metaText: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
});
