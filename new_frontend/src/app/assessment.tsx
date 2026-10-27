import { useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { answerTraitAssessment, getMe, startTraitAssessment } from '@/api/endpoints';
import { isApiError } from '@/api/client';
import type { TraitAssessmentRead } from '@/api/types';
import { AssessmentComplete } from '@/components/assessment/assessment-complete';
import { AssessmentProgress } from '@/components/assessment/assessment-progress';
import { LikertScale } from '@/components/assessment/likert-scale';
import { Button } from '@/components/ui/button';
import { ErrorState, InlineNotice, LoadingState } from '@/components/ui/states';
import { Surface } from '@/components/ui/surface';
import { Line, Space, Type } from '@/constants/tokens';
import { TRAIT_META } from '@/domain/traits';
import { useProfile } from '@/state/profile';
import { useSession } from '@/state/session';
import { useTheme } from '@/state/theme';

export default function AssessmentScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { setUser, logout } = useSession();
  const { refresh: refreshProfile } = useProfile();
  const [assessment, setAssessment] = useState<TraitAssessmentRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (restart = false) => {
    setLoading(true);
    setError(null);
    try {
      const next = await startTraitAssessment(restart);
      setAssessment(next);
      if (next.status === 'completed') {
        // The route guard reads the session user; refresh it so a completed
        // onboarding can leave /assessment instead of looping back.
        void getMe()
          .then((me) => setUser(me))
          .catch(() => undefined);
        refreshProfile();
      }
    } catch (caught) {
      setError(
        isApiError(caught)
          ? caught.message
          : '初始画像暂时不可用，请稍后再试。',
      );
    } finally {
      setLoading(false);
    }
  }, [refreshProfile, setUser]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial resume fetch
    void load(false);
  }, [load]);

  async function submitAnswer() {
    if (!assessment?.next_item || selected == null || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const next = await answerTraitAssessment(
        assessment.assessment_id,
        assessment.next_item.item_id,
        selected,
      );
      setAssessment(next);
      setSelected(null);
      if (next.status === 'completed') {
        void getMe()
          .then((me) => setUser(me))
          .catch(() => undefined);
        refreshProfile();
      }
    } catch (caught) {
      setError(isApiError(caught) ? caught.message : '提交失败，请重试。');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.page}>
        <LoadingState label="正在恢复初始画像…" />
      </View>
    );
  }

  if (error && !assessment) {
    return (
      <View style={styles.page}>
        <ErrorState
          title="初始画像暂时不可用"
          body={error}
          onRetry={() => void load(false)}
        />
      </View>
    );
  }

  if (!assessment) {
    return (
      <View style={styles.page}>
        <ErrorState
          title="没有拿到测评状态"
          body="请稍后重试。"
          onRetry={() => void load(false)}
        />
      </View>
    );
  }

  if (assessment.status === 'completed') {
    return (
      <View style={styles.page}>
        <AssessmentComplete
          traitProfile={assessment.trait_profile}
          onBack={() => router.push('/profile')}
          onRestart={() => void load(true)}
        />
      </View>
    );
  }

  const item = assessment.next_item;
  if (!item) {
    return (
      <View style={styles.page}>
        <ErrorState
          title="测评状态异常"
          body="后端没有返回下一道题。请重新开始测评。"
          onRetry={() => void load(true)}
        />
      </View>
    );
  }

  const domain = TRAIT_META[item.domain];
  const facet = item.facet_name || item.facet;

  return (
    <View style={styles.page}>
      <View style={styles.intro}>
        <View style={styles.introHead}>
          <Text style={[styles.title, { color: colors.ink }]}>初始画像</Text>
          <Button
            label="退出登录"
            variant="tonal"
            size="sm"
            disabled={submitting}
            onPress={logout}
          />
        </View>
        <Text style={[styles.body, { color: colors.inkMuted }]}>
          用于帮助系统了解比较稳定的个人特征，并改善后续计划分析。题目会按你的回答自适应选择，通常不需要做完固定 120 题。
        </Text>
      </View>

      <AssessmentProgress progress={assessment.progress} />

      {error ? (
        <InlineNotice
          message={error}
          onDismiss={() => setError(null)}
        />
      ) : null}

      <Surface level="level1" radius="lg">
        <View style={styles.card}>
          <View style={styles.itemMeta}>
            <Text style={[styles.dimension, { color: colors.primary }]}>{domain.name}</Text>
            {facet ? (
              <Text style={[styles.facet, { color: colors.inkFaint }]}>{facet}</Text>
            ) : null}
          </View>
          <Text style={[styles.question, { color: colors.ink }]}>{item.text}</Text>
          <LikertScale
            value={selected}
            onChange={setSelected}
            disabled={submitting}
          />
          <View style={styles.actions}>
            <Button
              label={submitting ? '提交中…' : '提交这一题'}
              variant="filled"
              disabled={selected == null || submitting}
              onPress={() => void submitAnswer()}
            />
            <Text style={[styles.note, { color: colors.inkFaint }]}>
              退出或刷新后会自动保存，下次回来可以继续。
            </Text>
          </View>
        </View>
      </Surface>

      <Text style={[styles.note, { color: colors.inkFaint }]}>
        这里只记录你的原始选择；计分和下一题选择都由后端模型完成。
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { gap: Space.xl },
  intro: { gap: Space.sm },
  introHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  title: { fontSize: Type.headlineSmall, fontWeight: '600' },
  body: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    maxWidth: 640,
  },
  card: { padding: Space.xl, gap: Space.lg },
  itemMeta: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  dimension: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
  },
  facet: { fontSize: Type.labelMedium },
  question: {
    fontSize: Type.titleLarge,
    lineHeight: Type.titleLarge * Line.relaxed,
    maxWidth: 640,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  note: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
    maxWidth: 560,
  },
});