import { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Banner } from '@/components/task/banner';
import { isEndAfterStart, isValidTime, parseEstimatedMinutes } from '@/components/task/task-form';
import { BottomSheet } from '@/components/ui/bottom-sheet';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { DateTimeField } from '@/components/ui/date-time-field';
import { useInteraction } from '@/components/ui/interaction';
import { Progress } from '@/components/ui/progress';
import { Segmented } from '@/components/ui/segmented';
import { TextField } from '@/components/ui/text-field';
import { Fonts, Line, Radius, Space, Type } from '@/constants/tokens';
import { formatShort, parseISO } from '@/domain/date';
import { TASK_KIND_LABEL, type Task } from '@/domain/task';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

const PRIORITIES = ['低', '中', '高'];
const PRIORITY_LABEL = ['低', '中', '高'];
const COGNITIVE_LABEL = { low: '低', medium: '中', high: '高' } as const;

function formatCalendarDay(date: string): string {
  const day = parseISO(date);
  return `${day.getMonth() + 1} 月 ${day.getDate()} 日`;
}

/**
 * The single place where a task can be inspected and acted on. Every action is
 * visible here, so nothing depends on hover or a hidden gesture.
 */
export function TaskDetailSheet({
  task,
  goalTitle,
  canEdit,
  onClose,
  onUpdateTask,
  onUpdateStandard,
  onToggleDone,
  onSetSkipped,
  onMoveTomorrow,
  onRequestDelete,
}: {
  task: Task;
  goalTitle: string | null;
  canEdit: boolean;
  onClose: () => void;
  onUpdateTask: (id: number, patch: Partial<Task>) => void;
  onUpdateStandard: (taskId: number, standardId: number, completed: boolean) => Promise<void>;
  onToggleDone: (id: number) => void;
  onSetSkipped: (id: number, skipped: boolean) => void;
  onMoveTomorrow: (id: number) => void;
  /** Ask the screen to confirm deletion; this sheet never opens its own modal. */
  onRequestDelete?: (id: number) => void;
}) {
  const { colors } = useTheme();
  const { actionError, clearActionError } = usePlan();

  const [title, setTitle] = useState(task.title);
  const [minutes, setMinutes] = useState(
    task.estimatedMinutes != null ? String(task.estimatedMinutes) : '',
  );
  const [priority, setPriority] = useState(Math.min(3, Math.max(1, task.priority)));
  const [dueDate, setDueDate] = useState(task.dueDate ?? '');
  const [startTime, setStartTime] = useState(task.startTime ?? '');
  const [endTime, setEndTime] = useState(task.endTime ?? '');

  const [titleError, setTitleError] = useState<string | null>(null);
  const [minutesError, setMinutesError] = useState<string | null>(null);
  const [timeError, setTimeError] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [standardBusy, setStandardBusy] = useState<number | null>(null);

  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const savedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      if (savedTimer.current) clearTimeout(savedTimer.current);
    },
    [],
  );

  const standards = [...task.standards].sort((a, b) => a.orderIndex - b.orderIndex);
  const completedStandards = standards.filter((standard) => standard.completed).length;
  const probability =
    task.completionProbability != null && Number.isFinite(task.completionProbability)
      ? Math.min(1, Math.max(0, task.completionProbability))
      : null;

  const timeText = task.startTime
    ? `${task.startTime}${task.endTime ? ` - ${task.endTime}` : ''}`
    : task.endTime
      ? `到 ${task.endTime}`
      : '未排时间';

  const seriesText =
    [
      task.seriesIndex != null ? `第 ${task.seriesIndex + 1} 天` : null,
      task.occurrenceDate ? formatCalendarDay(task.occurrenceDate) : null,
    ]
      .filter(Boolean)
      .join(' · ') || '未记录';

  const dailyTargetText =
    task.targetAmount != null
      ? `${task.targetAmount}${task.targetUnit ? ` ${task.targetUnit}` : ''}`
      : task.estimatedMinutes != null
        ? `${task.estimatedMinutes} 分钟`
        : '未设置';

  function save() {
    const nextTitle = title.trim();
    const nextMinutes = parseEstimatedMinutes(minutes);
    const nextStart = startTime.trim();
    const nextEnd = endTime.trim();

    let valid = true;
    if (!nextTitle) {
      setTitleError('标题不能为空。');
      valid = false;
    } else {
      setTitleError(null);
    }

    if (nextMinutes === 'invalid') {
      setMinutesError('填 1 到 600 分钟。');
      valid = false;
    } else {
      setMinutesError(null);
    }

    if (!isValidTime(nextStart) || !isValidTime(nextEnd)) {
      setTimeError('时间格式用 HH:MM，例如 09:30。');
      valid = false;
    } else if (nextEnd && !nextStart) {
      setTimeError('先填开始时间，再填结束时间。');
      valid = false;
    } else if (!isEndAfterStart(nextStart, nextEnd)) {
      setTimeError('结束时间要晚于开始时间。');
      valid = false;
    } else if ((nextStart || nextEnd) && !dueDate) {
      setTimeError('排了时间，也要选一个日期。');
      valid = false;
    } else {
      setTimeError(null);
    }

    if (!valid || nextMinutes === 'invalid') return;

    if (saveTimer.current) clearTimeout(saveTimer.current);
    if (savedTimer.current) clearTimeout(savedTimer.current);
    setSaved(false);
    setSaving(true);

    onUpdateTask(task.id, {
      title: nextTitle,
      estimatedMinutes: nextMinutes,
      priority,
      dueDate: dueDate || null,
      startTime: nextStart || null,
      dueTime: nextStart || null,
      endTime: nextEnd || null,
    });

    // `updateTask` is optimistic and returns void; give the save a beat so the
    // state change is visible, and keep the action error banner as the truth.
    saveTimer.current = setTimeout(() => {
      setSaving(false);
      setSaved(true);
      savedTimer.current = setTimeout(() => setSaved(false), 1800);
    }, 300);
  }

  async function toggleStandard(standardId: number, completed: boolean) {
    setStandardBusy(standardId);
    try {
      await onUpdateStandard(task.id, standardId, completed);
    } finally {
      setStandardBusy(null);
    }
  }

  return (
    <BottomSheet
      visible
      title="任务详情"
      subtitle={goalTitle ?? '未归入目标'}
      onClose={onClose}
      footer={
        <>
          <Button label="关闭" variant="text" onPress={onClose} />
          <Button label="今天先不做" variant="text" onPress={() => onMoveTomorrow(task.id)} />
          <Button
            label={task.skipped ? '取消跳过' : '跳过'}
            variant="tonal"
            onPress={() => onSetSkipped(task.id, !task.skipped)}
          />
          <Button
            label={task.done ? '取消完成' : '完成'}
            variant="filled"
            onPress={() => onToggleDone(task.id)}
          />
        </>
      }>
      {actionError ? (
        <Banner
          tone="error"
          title="操作没有完成"
          body={actionError}
          onDismiss={clearActionError}
        />
      ) : null}

      <View style={styles.titleBlock}>
        <Text
          style={[
            styles.title,
            {
              color: task.done || task.skipped ? colors.inkMuted : colors.ink,
              textDecorationLine: task.done ? 'line-through' : 'none',
            },
          ]}>
          {task.title}
        </Text>
        <View style={styles.tags}>
          {task.done ? <StatusTag label="已完成" tone={colors.primary} /> : null}
          {task.skipped ? <StatusTag label="已跳过" tone={colors.warning} /> : null}
        </View>
        {task.description ? (
          <Text style={[styles.description, { color: colors.inkMuted }]}>{task.description}</Text>
        ) : null}
      </View>

      <View style={styles.metaGrid}>
        <MetaItem label="目标" value={goalTitle ?? '未归入目标'} />
        <MetaItem label="类型" value={TASK_KIND_LABEL[task.taskKind]} />
        <MetaItem label="计划日期" value={task.dueDate ? formatShort(task.dueDate) : '未排日期'} />
        <MetaItem label="时间" value={timeText} mono />
        <MetaItem
          label="预计时长"
          value={task.estimatedMinutes != null ? `${task.estimatedMinutes} 分钟` : '未设置'}
          mono={task.estimatedMinutes != null}
        />
        {task.taskKind === 'long_term' ? (
          <MetaItem label="系列进度" value={seriesText} mono />
        ) : null}
        {task.taskKind !== 'one_off' ? (
          <MetaItem label="每日目标" value={dailyTargetText} mono={task.targetAmount != null} />
        ) : null}
        <MetaItem label="优先级" value={PRIORITY_LABEL[priority - 1] ?? '中'} />
        <MetaItem label="认知负荷" value={COGNITIVE_LABEL[task.cognitiveLoad]} />
        {task.predictedDuration != null ? (
          <MetaItem label="预测时长" value={`${task.predictedDuration} 分钟`} mono />
        ) : null}
      </View>

      {probability != null ? (
        <View style={styles.probability}>
          <View style={styles.sectionHead}>
            <Text style={[styles.sectionTitle, { color: colors.ink }]}>完成概率</Text>
            <Text style={[styles.counter, { color: colors.inkMuted }]}>
              {Math.round(probability * 100)}%
            </Text>
          </View>
          <Progress value={probability} />
        </View>
      ) : null}

      <View style={[styles.divider, { backgroundColor: colors.line }]} />

      <View style={styles.standards}>
        <View style={styles.sectionHead}>
          <Text style={[styles.sectionTitle, { color: colors.ink }]}>子步骤</Text>
          <Text style={[styles.counter, { color: colors.inkMuted }]}>
            {standardBusy != null ? '保存中…' : `${completedStandards} / ${standards.length}`}
          </Text>
        </View>
        {standards.length > 0 ? (
          <Progress
            value={standards.length === 0 ? 0 : completedStandards / standards.length}
            height={6}
          />
        ) : null}

        {standards.length === 0 ? (
          <Text style={[styles.note, { color: colors.inkMuted }]}>
            这个任务没有拆出子步骤。
          </Text>
        ) : (
          standards.map((standard) => (
            <View
              key={standard.id}
              style={[styles.standardRow, { borderTopColor: colors.outlineVariant }]}>
              <Checkbox
                checked={standard.completed}
                disabled={!canEdit || standardBusy === standard.id}
                label={`${standard.completed ? '取消完成' : '完成'}：${standard.description}`}
                onPress={() => {
                  void toggleStandard(standard.id, !standard.completed);
                }}
              />
              <View style={styles.standardCopy}>
                <Text
                  style={[
                    styles.standardTitle,
                    {
                      color: standard.completed ? colors.inkMuted : colors.ink,
                      textDecorationLine: standard.completed ? 'line-through' : 'none',
                    },
                  ]}>
                  {standard.description}
                </Text>
                {standard.estimatedDuration != null ? (
                  <Text style={[styles.note, { color: colors.inkFaint }]}>
                    约 {standard.estimatedDuration} 分钟
                  </Text>
                ) : null}
              </View>
            </View>
          ))
        )}
      </View>

      <View style={[styles.divider, { backgroundColor: colors.line }]} />

      {canEdit ? (
        <View style={styles.edit}>
          <Text style={[styles.sectionTitle, { color: colors.ink }]}>编辑任务</Text>

          <TextField
            label="标题"
            value={title}
            onChangeText={(value) => {
              setTitle(value);
              if (titleError) setTitleError(null);
            }}
            placeholder="要做什么？"
            error={titleError}
            background={colors.surfaceContainerLowest}
          />

          <TextField
            label="预计时长（分钟）"
            value={minutes}
            onChangeText={(value) => {
              setMinutes(value);
              if (minutesError) setMinutesError(null);
            }}
            placeholder="25"
            keyboardType="number-pad"
            error={minutesError}
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
                onChangeText={(value) => {
                  setStartTime(value);
                  if (timeError) setTimeError(null);
                }}
                placeholder="09:00"
                background={colors.surfaceContainerLowest}
              />
            </View>
            <View style={styles.timeField}>
              <TextField
                label="结束时间"
                value={endTime}
                onChangeText={(value) => {
                  setEndTime(value);
                  if (timeError) setTimeError(null);
                }}
                placeholder="09:30"
                background={colors.surfaceContainerLowest}
              />
            </View>
          </View>
          {timeError ? (
            <Text style={[styles.note, { color: colors.error }]}>{timeError}</Text>
          ) : (
            <Text style={[styles.note, { color: colors.inkFaint }]}>
              时间用 24 小时制 HH:MM；留空表示不排具体时间。
            </Text>
          )}

          <View style={styles.saveRow}>
            <Button
              label={saving ? '保存中…' : '保存修改'}
              variant="filled"
              disabled={saving}
              onPress={save}
            />
            {saved && !actionError ? (
              <Text style={[styles.saved, { color: colors.primary }]}>已保存</Text>
            ) : null}
          </View>
        </View>
      ) : (
        <Text style={[styles.note, { color: colors.inkMuted }]}>当前计划是只读的。</Text>
      )}

      {canEdit && onRequestDelete ? (
        <>
          <View style={[styles.divider, { backgroundColor: colors.line }]} />
          <View style={styles.danger}>
            <Text style={[styles.sectionTitle, { color: colors.error }]}>删除这个待办</Text>
            <Text style={[styles.note, { color: colors.inkMuted }]}>
              只从当前计划里移除，执行记录会保留。确认前会再问你一次。
            </Text>
            <DangerButton label="删除这个待办" onPress={() => onRequestDelete(task.id)} />
          </View>
        </>
      ) : null}
    </BottomSheet>
  );
}

function DangerButton({ label, onPress }: { label: string; onPress: () => void }) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      {...handlers}
      style={[
        styles.dangerButton,
        {
          borderColor: colors.error,
          backgroundColor: hovered ? colors.errorContainer : 'transparent',
          boxShadow: focused ? `0 0 0 2px ${colors.focusRing}` : undefined,
        },
      ]}>
      <Text style={[styles.dangerButtonText, { color: colors.error }]}>{label}</Text>
    </Pressable>
  );
}

function MetaItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  const { colors } = useTheme();
  return (
    <View style={styles.metaItem}>
      <Text style={[styles.metaLabel, { color: colors.inkFaint }]}>{label}</Text>
      <Text style={[styles.metaValue, mono && styles.mono, { color: colors.ink }]}>{value}</Text>
    </View>
  );
}

function StatusTag({ label, tone }: { label: string; tone: string }) {
  return <Text style={[styles.tag, { color: tone, borderColor: tone }]}>{label}</Text>;
}

const styles = StyleSheet.create({
  titleBlock: {
    gap: Space.sm,
  },
  title: {
    fontSize: Type.headlineSmall,
    lineHeight: Type.headlineSmall * Line.normal,
    fontWeight: '600',
  },
  tags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.sm,
  },
  tag: {
    borderWidth: 1,
    borderRadius: Radius.pill,
    paddingHorizontal: Space.sm,
    paddingVertical: 2,
    fontSize: Type.labelSmall,
    overflow: 'hidden',
  },
  description: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
  },
  metaGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  metaItem: {
    flexGrow: 1,
    flexBasis: 140,
    minWidth: 110,
    gap: 2,
  },
  metaLabel: {
    fontSize: Type.labelSmall,
  },
  metaValue: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.normal,
  },
  mono: {
    fontFamily: Fonts.monoRegular,
  },
  probability: {
    gap: Space.sm,
  },
  sectionHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  sectionTitle: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  counter: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  divider: {
    height: 1,
  },
  standards: {
    gap: Space.sm,
  },
  standardRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Space.sm,
    borderTopWidth: 1,
    paddingVertical: Space.xs,
  },
  standardCopy: {
    flex: 1,
    minWidth: 0,
    gap: 2,
    paddingTop: Space.md,
  },
  standardTitle: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.normal,
  },
  note: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  edit: {
    gap: Space.lg,
  },
  danger: {
    gap: Space.sm,
  },
  dangerButton: {
    alignSelf: 'flex-start',
    minHeight: 44,
    paddingHorizontal: Space.xl,
    borderWidth: 1,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dangerButtonText: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
  },
  timeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  timeField: {
    flexGrow: 1,
    flexBasis: 140,
  },
  saveRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: Space.md,
  },
  saved: {
    fontSize: Type.labelMedium,
    fontWeight: '600',
  },
});
