import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { DateTimeField } from '@/components/ui/date-time-field';
import { Dialog } from '@/components/ui/dialog';
import { Segmented } from '@/components/ui/segmented';
import { TextField } from '@/components/ui/text-field';
import { Space } from '@/constants/tokens';
import { todayISO } from '@/domain/date';
import { useTheme } from '@/state/theme';

const PRIORITIES = ['低', '中', '高'];

export type PendingTaskInput = {
  title: string;
  priority: number;
  dueDate: string | null;
  notes: string;
};

/** Add (or edit) one item in the "waiting to be decomposed" list on the GOAL page. */
export function TaskAddDialog({
  initial,
  onClose,
  onSubmit,
}: {
  initial?: PendingTaskInput;
  onClose: () => void;
  onSubmit: (input: PendingTaskInput) => void;
}) {
  const { colors } = useTheme();
  const [title, setTitle] = useState(initial?.title ?? '');
  const [priority, setPriority] = useState(initial?.priority ?? 2);
  const [dueDate, setDueDate] = useState<string | null>(initial?.dueDate ?? todayISO());
  const [notes, setNotes] = useState(initial?.notes ?? '');
  const canSubmit = title.trim().length > 0;

  return (
    <Dialog
      visible
      title={initial ? '编辑任务' : '添加任务'}
      description="这些是等待拆解的任务；点「拆解」时它们会一起交给系统排进每天。"
      onRequestClose={onClose}
      actions={[
        { label: '取消', variant: 'text', onPress: onClose },
        {
          label: initial ? '保存' : '添加',
          variant: 'filled',
          disabled: !canSubmit,
          onPress: () => onSubmit({ title: title.trim(), priority, dueDate, notes: notes.trim() }),
        },
      ]}>
      <TextField
        label="任务名称"
        value={title}
        onChangeText={setTitle}
        placeholder="例如：复习高数极限"
        autoFocus
        background={colors.surfaceContainerLowest}
      />
      <Segmented
        label="优先级"
        options={PRIORITIES}
        value={priority - 1}
        onChange={(index) => setPriority(index + 1)}
      />
      <DateTimeField
        label="完成日期"
        date={dueDate ?? ''}
        time=""
        withTime={false}
        onChangeDate={(value) => setDueDate(value ?? null)}
        onChangeTime={() => undefined}
      />
      <TextField
        label="补充（选填）"
        value={notes}
        onChangeText={setNotes}
        placeholder="拆解线索，比如：看课 / 做例题 / 做练习"
        multiline
        background={colors.surfaceContainerLowest}
      />
      <View style={styles.spacer} />
    </Dialog>
  );
}

const styles = StyleSheet.create({
  spacer: {
    height: Space.xs,
  },
});
