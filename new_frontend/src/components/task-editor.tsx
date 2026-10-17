import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { isEndAfterStart, isValidTime, parseEstimatedMinutes } from '@/components/task/task-form';
import { Dialog } from '@/components/ui/dialog';
import { DateTimeField } from '@/components/ui/date-time-field';
import { Segmented } from '@/components/ui/segmented';
import { TextField } from '@/components/ui/text-field';
import { Space, Type } from '@/constants/tokens';
import type { Task } from '@/domain/task';
import { useTheme } from '@/state/theme';

const PRIORITIES = ['低', '中', '高'];

/**
 * Focused editor for the fields the API actually supports. Repeat/isNew
 * branches were removed: they only ever ran in the local mock store.
 */
export function TaskEditor({
  task,
  onClose,
  onSave,
}: {
  task: Task;
  onClose: () => void;
  onSave: (id: number, patch: Partial<Task>) => void;
}) {
  const { colors } = useTheme();
  const [title, setTitle] = useState(task.title);
  const [minutes, setMinutes] = useState(
    task.estimatedMinutes != null ? String(task.estimatedMinutes) : '',
  );
  const [priority, setPriority] = useState(Math.min(3, Math.max(1, task.priority)));
  const [dueDate, setDueDate] = useState(task.dueDate ?? '');
  const [startTime, setStartTime] = useState(task.startTime ?? '');
  const [endTime, setEndTime] = useState(task.endTime ?? '');
  const [error, setError] = useState<string | null>(null);

  function save() {
    const nextTitle = title.trim();
    const nextMinutes = parseEstimatedMinutes(minutes);
    const nextStart = startTime.trim();
    const nextEnd = endTime.trim();

    if (!nextTitle) {
      setError('标题不能为空。');
      return;
    }
    if (nextMinutes === 'invalid') {
      setError('预计时长填 1 到 600 分钟。');
      return;
    }
    if (!isValidTime(nextStart) || !isValidTime(nextEnd)) {
      setError('时间格式用 HH:MM。');
      return;
    }
    if (nextEnd && !nextStart) {
      setError('先填开始时间，再填结束时间。');
      return;
    }
    if (!isEndAfterStart(nextStart, nextEnd)) {
      setError('结束时间要晚于开始时间。');
      return;
    }
    if ((nextStart || nextEnd) && !dueDate) {
      setError('排了时间，也要选一个日期。');
      return;
    }

    onSave(task.id, {
      title: nextTitle,
      estimatedMinutes: nextMinutes,
      priority,
      dueDate: dueDate || null,
      startTime: nextStart || null,
      dueTime: nextStart || null,
      endTime: nextEnd || null,
    });
    onClose();
  }

  return (
    <Dialog
      visible
      width={560}
      title="编辑任务"
      description="只显示后端能保存的字段；删除任务和重复规则不在当前 API 里。"
      onRequestClose={onClose}
      actions={[
        { label: '取消', variant: 'text', onPress: onClose },
        { label: '保存', variant: 'filled', onPress: save },
      ]}>
      <TextField
        label="标题"
        value={title}
        onChangeText={setTitle}
        placeholder="要做什么？"
        background={colors.surfaceContainerLowest}
      />
      <TextField
        label="预计时长（分钟）"
        value={minutes}
        onChangeText={setMinutes}
        placeholder="25"
        keyboardType="number-pad"
        background={colors.surfaceContainerLowest}
      />
      <Segmented
        label="优先级"
        options={PRIORITIES}
        value={priority - 1}
        onChange={(index) => setPriority(index + 1)}
      />
      <DateTimeField
        label="计划日期"
        date={dueDate}
        time=""
        withTime={false}
        onChangeDate={(value) => setDueDate(value ?? '')}
        onChangeTime={() => undefined}
      />
      <View style={styles.timeRow}>
        <View style={styles.timeField}>
          <TextField
            label="开始时间"
            value={startTime}
            onChangeText={setStartTime}
            placeholder="09:00"
            background={colors.surfaceContainerLowest}
          />
        </View>
        <View style={styles.timeField}>
          <TextField
            label="结束时间"
            value={endTime}
            onChangeText={setEndTime}
            placeholder="09:30"
            background={colors.surfaceContainerLowest}
          />
        </View>
      </View>
      {error ? <Text style={[styles.error, { color: colors.error }]}>{error}</Text> : null}
    </Dialog>
  );
}

const styles = StyleSheet.create({
  timeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  timeField: {
    flexGrow: 1,
    flexBasis: 140,
  },
  error: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * 1.5,
  },
});
