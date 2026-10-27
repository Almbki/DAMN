import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { ClarificationRead } from '@/api/types';
import { Dialog } from '@/components/ui/dialog';
import { TextField } from '@/components/ui/text-field';
import { Line, Space, Type } from '@/constants/tokens';
import { useTheme } from '@/state/theme';

/** Simple v1 clarification form: all questions at once, text inputs only. */
export function ClarificationDialog({
  clarification,
  busy,
  onSubmit,
  onClose,
}: {
  clarification: ClarificationRead;
  busy: boolean;
  onSubmit: (answers: { goalId: number; field: string; answer: string }[]) => void;
  onClose: () => void;
}) {
  const { colors } = useTheme();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const key = (goalId: number, field: string) => `${goalId}:${field}`;
  const canSubmit = clarification.questions.every(
    (q) => !q.required || (answers[key(q.goal_id, q.field)] ?? '').trim().length > 0,
  );

  function submit() {
    onSubmit(
      clarification.questions
        .map((q) => ({
          goalId: q.goal_id,
          field: q.field,
          answer: (answers[key(q.goal_id, q.field)] ?? '').trim(),
        }))
        .filter((answer) => answer.answer.length > 0),
    );
  }

  return (
    <Dialog
      visible
      width={520}
      title="还需要一些信息"
      description="补充后系统才能准确拆解；本次不会生成部分计划。"
      onRequestClose={onClose}
      actions={[
        { label: '取消', variant: 'text', onPress: onClose },
        {
          label: '继续生成计划',
          variant: 'filled',
          disabled: busy || !canSubmit,
          onPress: submit,
        },
      ]}>
      {clarification.questions.map((q) => (
        <View key={key(q.goal_id, q.field)} style={styles.field}>
          <Text style={[styles.question, { color: colors.ink }]}>{q.question}</Text>
          <TextField
            label={q.field}
            value={answers[key(q.goal_id, q.field)] ?? ''}
            onChangeText={(value) =>
              setAnswers((prev) => ({ ...prev, [key(q.goal_id, q.field)]: value }))
            }
            placeholder="请输入"
            background={colors.surfaceContainerLowest}
          />
        </View>
      ))}
    </Dialog>
  );
}

const styles = StyleSheet.create({
  field: {
    gap: Space.xs,
  },
  question: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
    fontWeight: '600',
  },
});
