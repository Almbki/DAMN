import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { parseEstimatedMinutes } from '@/components/task/task-form';
import {
  ALL_WEEKDAYS,
  WeekdayPicker,
  WEEKDAY_PRESETS,
  daysForPreset,
  presetFromWeekdays,
} from '@/components/task/weekday-picker';
import { DateTimeField } from '@/components/ui/date-time-field';
import { Dialog } from '@/components/ui/dialog';
import { Segmented } from '@/components/ui/segmented';
import { TextField } from '@/components/ui/text-field';
import { Line, Space, Type } from '@/constants/tokens';
import { todayISO } from '@/domain/date';
import type { TaskKind } from '@/domain/task';
import type { PendingTaskInput } from '@/state/plan-context';
import { useTheme } from '@/state/theme';

export type { PendingTaskInput };

const PRIORITIES = ['低', '中', '高'];
const KINDS: TaskKind[] = ['one_off', 'long_term', 'routine'];
const KIND_LABELS = ['一次性', '长期', '常规'];

/** `null` when blank, `invalid` when not a positive whole number. */
function parseTargetAmount(value: string): number | null | 'invalid' {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^\d+$/.test(trimmed)) return 'invalid';
  const amount = Number(trimmed);
  if (!Number.isInteger(amount) || amount < 1 || amount > 9999) return 'invalid';
  return amount;
}

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
  const [kindIndex, setKindIndex] = useState(() =>
    Math.max(0, KINDS.indexOf(initial?.taskKind ?? 'one_off')),
  );
  const [priority, setPriority] = useState(initial?.priority ?? 2);
  const [dueDate, setDueDate] = useState<string | null>(
    initial ? initial.dueDate : todayISO(),
  );
  const [notes, setNotes] = useState(initial?.notes ?? '');

  const [startDate, setStartDate] = useState<string | null>(
    initial ? (initial.startDate ?? null) : todayISO(),
  );
  const [dailyTarget, setDailyTarget] = useState(
    initial?.dailyTargetMinutes != null ? String(initial.dailyTargetMinutes) : '',
  );
  const [weekdays, setWeekdays] = useState<number[]>(() =>
    initial?.recurrenceWeekdays
      ? Array.from(new Set(initial.recurrenceWeekdays)).sort((a, b) => a - b)
      : [...ALL_WEEKDAYS],
  );
  const [repeatPreset, setRepeatPreset] = useState(() =>
    presetFromWeekdays(initial?.recurrenceWeekdays),
  );
  const [targetAmount, setTargetAmount] = useState(
    initial?.targetAmount != null ? String(initial.targetAmount) : '',
  );
  const [targetUnit, setTargetUnit] = useState(initial?.targetUnit ?? '');
  const [seriesError, setSeriesError] = useState<string | null>(null);
  const [dateError, setDateError] = useState<string | null>(null);

  const kind = KINDS[kindIndex];
  const isSeries = kind !== 'one_off';
  const canSubmit = title.trim().length > 0;

  function changeKind(index: number) {
    setKindIndex(index);
    setSeriesError(null);
  }

  function changePreset(index: number) {
    setRepeatPreset(index);
    setSeriesError(null);
    const days = daysForPreset(index);
    if (days) setWeekdays(days);
  }

  function changeWeekdays(days: number[]) {
    setWeekdays(days);
    if (seriesError) setSeriesError(null);
  }

  function submit() {
    const minutes = parseEstimatedMinutes(dailyTarget);
    const amount = parseTargetAmount(targetAmount);
    const today = todayISO();

    if (startDate && startDate < today) {
      setDateError('开始日期不能早于今天。');
      return;
    }
    if (dueDate && dueDate < today) {
      setDateError('结束日期不能早于今天。');
      return;
    }
    if (isSeries && startDate && dueDate && dueDate < startDate) {
      setDateError('结束日期不能早于开始日期。');
      return;
    }
    setDateError(null);

    if (isSeries) {
      if (minutes === 'invalid') {
        setSeriesError('每天投入填 1 到 600 分钟。');
        return;
      }
      if (amount === 'invalid') {
        setSeriesError('目标量填 1 到 9999 之间的整数。');
        return;
      }
      if (startDate && dueDate && dueDate < startDate) {
        setSeriesError('结束日期不能早于开始日期。');
        return;
      }
      if (weekdays.length === 0) {
        setSeriesError('至少选一个重复日。');
        return;
      }
    }

    onSubmit({
      title: title.trim(),
      priority,
      dueDate,
      notes: notes.trim(),
      taskKind: kind,
      startDate: isSeries ? startDate : null,
      dailyTargetMinutes: isSeries && minutes !== 'invalid' ? minutes : null,
      recurrenceWeekdays: isSeries ? weekdays : null,
      targetAmount: isSeries && amount !== 'invalid' ? amount : null,
      targetUnit:
        isSeries && amount != null && amount !== 'invalid'
          ? targetUnit.trim() || '次'
          : null,
    });
  }

  return (
    <Dialog
      visible
      width={520}
      title={initial ? '编辑任务' : '添加任务'}
      description="这些是等待拆解的任务；点「拆解」时它们会一起交给系统排进每天。"
      onRequestClose={onClose}
      actions={[
        { label: '取消', variant: 'text', onPress: onClose },
        {
          label: initial ? '保存' : '添加',
          variant: 'filled',
          disabled: !canSubmit,
          onPress: submit,
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
        label="类型"
        options={KIND_LABELS}
        value={kindIndex}
        onChange={changeKind}
      />
      <Segmented
        label="优先级"
        options={PRIORITIES}
        value={priority - 1}
        onChange={(index) => setPriority(index + 1)}
      />

      {isSeries ? (
        <>
          <View style={styles.dateRow}>
            <View style={styles.dateField}>
              <DateTimeField
                label="开始日期"
                date={startDate ?? ''}
                time=""
                withTime={false}
                minDate={todayISO()}
                onChangeDate={(value) => {
                  setStartDate(value);
                  setDateError(null);
                  if (seriesError) setSeriesError(null);
                }}
                onChangeTime={() => undefined}
              />
            </View>
            <View style={styles.dateField}>
              <DateTimeField
                label="结束日期"
                date={dueDate ?? ''}
                time=""
                withTime={false}
                minDate={startDate ?? todayISO()}
                onChangeDate={(value) => {
                  setDueDate(value);
                  setDateError(null);
                  if (seriesError) setSeriesError(null);
                }}
                onChangeTime={() => undefined}
              />
            </View>
          </View>

          <TextField
            label="每天投入（分钟）"
            value={dailyTarget}
            onChangeText={(value) => {
              setDailyTarget(value);
              if (seriesError) setSeriesError(null);
            }}
            placeholder="60"
            keyboardType="number-pad"
            background={colors.surfaceContainerLowest}
          />

          <Segmented
            label="重复日"
            options={WEEKDAY_PRESETS}
            value={repeatPreset}
            onChange={changePreset}
          />
          {repeatPreset === 3 ? (
            <WeekdayPicker
              value={weekdays}
              onChange={changeWeekdays}
              error={weekdays.length === 0 ? '至少选一个重复日。' : null}
            />
          ) : null}

          <View style={styles.targetRow}>
            <View style={styles.targetAmount}>
              <TextField
                label="目标量（选填）"
                value={targetAmount}
                onChangeText={(value) => {
                  setTargetAmount(value);
                  if (seriesError) setSeriesError(null);
                }}
                placeholder="10"
                keyboardType="number-pad"
                background={colors.surfaceContainerLowest}
              />
            </View>
            <View style={styles.targetUnit}>
              <TextField
                label="单位"
                value={targetUnit}
                onChangeText={setTargetUnit}
                placeholder="题 / 页"
                background={colors.surfaceContainerLowest}
              />
            </View>
          </View>

          {seriesError ? (
            <Text style={[styles.error, { color: colors.error }]}>{seriesError}</Text>
          ) : (
            <Text style={[styles.hint, { color: colors.inkMuted }]}>
              后端会把长期/常规目标拆成每天的条目；结束日期留空表示不设终点。
            </Text>
          )}
        </>
      ) : (
        <DateTimeField
          label="完成日期"
          date={dueDate ?? ''}
          time=""
          withTime={false}
          onChangeDate={(value) => setDueDate(value ?? null)}
          onChangeTime={() => undefined}
        />
      )}

      <View style={styles.notesField}>
        <TextField
          label="补充（选填）"
          value={notes}
          onChangeText={setNotes}
          placeholder="可写步骤或细节，比如：看课 / 做例题 / 做练习"
          multiline
          background={colors.surfaceContainerLowest}
        />
        <Text style={[styles.hint, { color: colors.inkMuted }]}>
          填写后系统会据此生成子步骤；留空则不生成子步骤。
        </Text>
      </View>
      {dateError ? (
        <Text style={[styles.error, { color: colors.error }]}>{dateError}</Text>
      ) : null}
      <View style={styles.spacer} />
    </Dialog>
  );
}

const styles = StyleSheet.create({
  spacer: {
    height: Space.xs,
  },
  dateRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  dateField: {
    flexGrow: 1,
    flexBasis: 200,
  },
  targetRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  targetAmount: {
    flexGrow: 2,
    flexBasis: 160,
  },
  targetUnit: {
    flexGrow: 1,
    flexBasis: 110,
  },
  notesField: {
    gap: Space.xs,
  },
  hint: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  error: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
    fontWeight: '600',
  },
});
