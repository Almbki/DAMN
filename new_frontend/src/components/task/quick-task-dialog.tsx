import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Dialog } from '@/components/ui/dialog';
import { Segmented } from '@/components/ui/segmented';
import { TextField } from '@/components/ui/text-field';
import { Space } from '@/constants/tokens';
import { todayISO } from '@/domain/date';
import type { NewTaskInput } from '@/domain/task-ops';
import { useTheme } from '@/state/theme';

import { parseEstimatedMinutes } from './task-form';

const PRIORITIES = ['低', '中', '高'];

/** Mock-mode quick add. API mode sends people to the 目标 screen instead. */
export function QuickTaskDialog({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (input: NewTaskInput) => void;
}) {
  const { colors } = useTheme();
  const [title, setTitle] = useState('');
  const [priority, setPriority] = useState(2);
  const [minutes, setMinutes] = useState('');
  const [minutesError, setMinutesError] = useState<string | null>(null);

  function changeMinutes(value: string) {
    setMinutes(value);
    const parsed = parseEstimatedMinutes(value);
    setMinutesError(parsed === 'invalid' ? '填 1 到 600 分钟。' : null);
  }

  function submit() {
    const parsed = parseEstimatedMinutes(minutes);
    if (parsed === 'invalid') {
      setMinutesError('填 1 到 600 分钟。');
      return;
    }
    onCreate({
      title: title.trim(),
      priority,
      dueDate: todayISO(),
      estimatedMinutes: parsed,
      cognitiveLoad: 'medium',
    });
    onClose();
  }

  const canSubmit = title.trim().length > 0 && minutesError == null;

  return (
    <Dialog
      visible
      width={480}
      title="添加今天的小事"
      description="只建一条今天要做的事。需要系统拆解和排期时，去「目标」页。"
      onRequestClose={onClose}
      actions={[
        { label: '取消', variant: 'text', onPress: onClose },
        { label: '添加', variant: 'filled', disabled: !canSubmit, onPress: submit },
      ]}>
      <TextField
        label="要做什么"
        value={title}
        onChangeText={setTitle}
        placeholder="例如：整理今天的笔记"
        autoFocus
        background={colors.surfaceContainerLowest}
      />
      <Segmented
        label="优先级"
        options={PRIORITIES}
        value={priority - 1}
        onChange={(index) => setPriority(index + 1)}
      />
      <TextField
        label="预计时长（分钟）"
        value={minutes}
        onChangeText={changeMinutes}
        placeholder="25"
        keyboardType="number-pad"
        error={minutesError}
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
