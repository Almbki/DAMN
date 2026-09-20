import { useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { DateTimeField } from '@/components/ui/date-time-field';
import { Segmented } from '@/components/ui/segmented';
import { TextField } from '@/components/ui/text-field';
import { Radius, Space, Type } from '@/constants/tokens';
import {
  REPEAT_ENDS,
  REPEAT_END_LABEL,
  REPEAT_FREQS,
  REPEAT_FREQ_LABEL,
  type RepeatEnd,
  type RepeatFreq,
  type Task,
} from '@/domain/task';
import { useTheme } from '@/state/theme';

export function TaskEditor({
  task,
  isNew = false,
  onClose,
  onSave,
  onDelete,
  onMove,
}: {
  task: Task;
  isNew?: boolean;
  onClose: () => void;
  onSave: (id: number, patch: Partial<Task>) => void;
  onDelete: (id: number) => void;
  onMove: (id: number, delta: number) => void;
}) {
  const { colors } = useTheme();
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description);
  const [notes, setNotes] = useState(task.notes);
  const [startDate, setStartDate] = useState(task.startDate ?? '');
  const [startTime, setStartTime] = useState(task.startTime ?? '');
  const [dueDate, setDueDate] = useState(task.dueDate ?? '');
  const [dueTime, setDueTime] = useState(task.dueTime ?? '');
  const [minutes, setMinutes] = useState(task.estimatedMinutes ? String(task.estimatedMinutes) : '');
  const [repeatFreq, setRepeatFreq] = useState<RepeatFreq>(task.repeat.freq);
  const [repeatInterval, setRepeatInterval] = useState(task.repeat.interval);
  const [repeatEnd, setRepeatEnd] = useState<RepeatEnd>(task.repeat.end);
  const [repeatUntil, setRepeatUntil] = useState(task.repeat.until ?? '');
  const [repeatCount, setRepeatCount] = useState(task.repeat.count ? String(task.repeat.count) : '');

  function save() {
    onSave(task.id, {
      title: title.trim() || '未命名任务',
      description,
      notes,
      startDate: startDate || null,
      startTime: startTime || null,
      dueDate: dueDate || null,
      dueTime: dueTime || null,
      estimatedMinutes: minutes.trim() ? Number(minutes) || null : null,
      repeat:
        repeatFreq === 'none'
          ? { freq: 'none', interval: 1, end: 'never', until: null, count: null }
          : {
              freq: repeatFreq,
              interval: Math.max(1, repeatInterval),
              end: repeatEnd,
              until: repeatEnd === 'until' ? repeatUntil || null : null,
              count: repeatEnd === 'count' ? Math.max(1, Number(repeatCount) || 1) : null,
            },
    });
    onClose();
  }

  const intervalUnit = repeatFreq === 'weekly' ? '周' : repeatFreq === 'monthly' ? '个月' : '天';

  return (
    <Modal transparent animationType="fade" visible onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={[styles.panel, { backgroundColor: colors.paper, borderColor: colors.line }]}>
          <ScrollView contentContainerStyle={styles.panelContent}>
            <Text style={[styles.heading, { color: colors.ink }]}>{isNew ? '新建任务' : '编辑任务'}</Text>

            <TextField label="标题" value={title} onChangeText={setTitle} placeholder="要做什么？" autoFocus={isNew} testID="editor-title" />
            <TextField label="描述" value={description} onChangeText={setDescription} placeholder="一句话说明" />
            <TextField label="备注" value={notes} onChangeText={setNotes} placeholder="补充信息、链接…" multiline />

            <DateTimeField
              label="开始"
              date={startDate}
              time={startTime}
              onChangeDate={(value) => setStartDate(value ?? '')}
              onChangeTime={(value) => setStartTime(value ?? '')}
            />
            <DateTimeField
              label="截止"
              date={dueDate}
              time={dueTime}
              onChangeDate={(value) => setDueDate(value ?? '')}
              onChangeTime={(value) => setDueTime(value ?? '')}
            />

            <TextField label="预计时长（分钟）" value={minutes} onChangeText={setMinutes} placeholder="25" keyboardType="number-pad" />

            <View style={styles.repeatBlock}>
              <Segmented
                label="重复"
                options={REPEAT_FREQS.map((item) => REPEAT_FREQ_LABEL[item])}
                value={REPEAT_FREQS.indexOf(repeatFreq)}
                onChange={(index) => setRepeatFreq(REPEAT_FREQS[index] as RepeatFreq)}
              />
              {repeatFreq !== 'none' ? (
                <>
                  <View style={styles.stepperRow}>
                    <Text style={[styles.stepperLabel, { color: colors.inkMuted }]}>频率</Text>
                    <Stepper
                      value={repeatInterval}
                      unit={intervalUnit}
                      onChange={(next) => setRepeatInterval(Math.max(1, next))}
                    />
                  </View>
                  <Segmented
                    label="结束条件"
                    options={REPEAT_ENDS.map((item) => REPEAT_END_LABEL[item])}
                    value={REPEAT_ENDS.indexOf(repeatEnd)}
                    onChange={(index) => setRepeatEnd(REPEAT_ENDS[index] as RepeatEnd)}
                  />
                  {repeatEnd === 'until' ? (
                    <DateTimeField
                      label="重复到"
                      date={repeatUntil}
                      time=""
                      withTime={false}
                      onChangeDate={(value) => setRepeatUntil(value ?? '')}
                      onChangeTime={() => undefined}
                    />
                  ) : null}
                  {repeatEnd === 'count' ? (
                    <TextField label="重复次数" value={repeatCount} onChangeText={setRepeatCount} placeholder="5" keyboardType="number-pad" />
                  ) : null}
                </>
              ) : null}
            </View>

            <View style={styles.actions}>
              <Button label="保存" variant="primary" onPress={save} />
              {!isNew ? (
                <>
                  <Button label="上移" variant="ghost" onPress={() => onMove(task.id, -1)} />
                  <Button label="下移" variant="ghost" onPress={() => onMove(task.id, 1)} />
                  <Button label="删除" variant="secondary" onPress={() => { onDelete(task.id); onClose(); }} />
                </>
              ) : null}
              <Button label="关闭" variant="ghost" onPress={onClose} />
            </View>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

function Stepper({ value, unit, onChange }: { value: number; unit: string; onChange: (value: number) => void }) {
  const { colors } = useTheme();
  return (
    <View style={styles.stepper}>
      <Pressable accessibilityRole="button" accessibilityLabel="减少" onPress={() => onChange(value - 1)} style={[styles.stepperBtn, { borderColor: colors.line }]}>
        <Text style={[styles.stepperBtnText, { color: colors.ink }]}>−</Text>
      </Pressable>
      <Text style={[styles.stepperValue, { color: colors.ink }]}>每 {value} {unit}</Text>
      <Pressable accessibilityRole="button" accessibilityLabel="增加" onPress={() => onChange(value + 1)} style={[styles.stepperBtn, { borderColor: colors.line }]}>
        <Text style={[styles.stepperBtnText, { color: colors.ink }]}>＋</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: Space.lg,
  },
  panel: {
    width: '100%',
    maxWidth: 560,
    maxHeight: '92%',
    borderWidth: 1,
    borderRadius: Radius.md,
    overflow: 'hidden',
  },
  panelContent: {
    padding: Space.xl,
    gap: Space.lg,
  },
  heading: {
    fontSize: Type.title,
    fontWeight: '700',
  },
  repeatBlock: {
    gap: Space.lg,
  },
  stepperRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
  },
  stepperLabel: {
    fontSize: Type.small,
  },
  stepper: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  stepperBtn: {
    width: 36,
    height: 36,
    borderWidth: 1,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepperBtnText: {
    fontSize: Type.bodyLg,
  },
  stepperValue: {
    fontSize: Type.body,
    minWidth: 76,
    textAlign: 'center',
  },
  actions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Space.sm,
    paddingTop: Space.sm,
  },
});
