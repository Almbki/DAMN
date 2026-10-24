import { StyleSheet, Text, View } from 'react-native';

import type { TraitAssessmentProgress } from '@/api/types';
import { Progress } from '@/components/ui/progress';
import { Fonts, Line, Space, Type } from '@/constants/tokens';
import { TRAIT_META } from '@/domain/traits';
import { useTheme } from '@/state/theme';

/** Soft progress: counts and the current dimension only. No model internals. */
export function AssessmentProgress({ progress }: { progress: TraitAssessmentProgress }) {
  const { colors } = useTheme();
  const current = progress.current_domain ? TRAIT_META[progress.current_domain] : null;
  const totalHint = Math.max(1, progress.answered + progress.remaining_max);
  const value = Math.min(1, progress.answered / totalHint);

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        <Text style={[styles.label, { color: colors.inkMuted }]}>
          已答 {progress.answered} 题
        </Text>
        <Text style={[styles.range, { color: colors.inkFaint }]}>
          预计还需 {progress.remaining_min}–{progress.remaining_max} 题
        </Text>
      </View>
      <Progress value={value} height={6} color={colors.primary} />
      <Text style={[styles.current, { color: colors.inkMuted }]}>
        {current ? `当前维度：${current.name}` : '正在收尾'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: Space.sm },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  label: {
    fontFamily: Fonts.mono,
    fontSize: Type.labelLarge,
  },
  range: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
  },
  current: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.normal,
  },
});