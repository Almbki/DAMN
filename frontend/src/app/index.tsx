import { useCallback, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View, useWindowDimensions } from 'react-native';

import { hhmm, minutesLabel } from '@/api/format';
import type { TaskRead } from '@/api/types';
import { Ruler, type RulerSegment } from '@/components/ruler';
import { Button } from '@/components/ui/button';
import { useInteraction } from '@/components/ui/interaction';
import { EmptyState } from '@/components/ui/states';
import { WhyNote } from '@/components/why-note';
import { Layout, Line, Radius, Space, Type } from '@/constants/tokens';
import { mockWhyNow } from '@/data/mock';
import { useListKeys } from '@/hooks/use-list-keys';
import { energyLabel, usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

export default function TodoScreen() {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const wide = width > 0 && width >= Layout.breakpoint;
  const {
    tasks,
    currentTask,
    ruler,
    energy,
    completedCount,
    totalCount,
    remainingMinutes,
    addGoal,
    toggleTask,
    skipTask,
    startTask,
  } = usePlan();
  const [draft, setDraft] = useState('');
  const [activeId, setActiveId] = useState<number | null>(null);

  const move = useCallback(
    (delta: number) => {
      if (tasks.length === 0) return;
      setActiveId((current) => {
        const fromId = current ?? currentTask?.id ?? tasks[0].id;
        const index = tasks.findIndex((task) => task.id === fromId);
        const next = Math.min(tasks.length - 1, Math.max(0, index + delta));
        return tasks[next].id;
      });
    },
    [tasks, currentTask],
  );

  const toggleActive = useCallback(() => {
    const id = activeId ?? currentTask?.id ?? tasks[0]?.id;
    if (id == null) return;
    setActiveId(id);
    toggleTask(id);
  }, [activeId, currentTask, tasks, toggleTask]);

  const skipActive = useCallback(() => {
    const id = activeId ?? currentTask?.id ?? tasks[0]?.id;
    if (id == null) return;
    setActiveId(id);
    skipTask(id);
  }, [activeId, currentTask, tasks, skipTask]);

  useListKeys({ onPrev: () => move(-1), onNext: () => move(1), onToggle: toggleActive, onSkip: skipActive });

  function submitGoal() {
    if (!draft.trim()) return;
    addGoal(draft);
    setDraft('');
  }

  return (
    <View style={styles.page}>
      <AddGoalBar value={draft} onChange={setDraft} onSubmit={submitGoal} />

      {currentTask ? (
        <NowCard
          task={currentTask}
          ruler={ruler}
          energyLabelText={energyLabel[energy]}
          onStart={() => startTask(currentTask.id)}
          onSkip={() => skipTask(currentTask.id)}
        />
      ) : (
        <EmptyState
          title="今天没有安排"
          body="在上面写下一个目标，我来把它拆成今天能做完的几步。"
        />
      )}

      <View style={styles.section}>
        <View style={styles.sectionHead}>
          <Text style={[styles.sectionTitle, { color: colors.ink }]}>今天的任务</Text>
          <Text style={[styles.sectionMeta, { color: colors.inkMuted }]}>
            共 <Text style={styles.mono}>{totalCount}</Text> 件 · 剩余{' '}
            <Text style={styles.mono}>{remainingMinutes}</Text> 分钟
          </Text>
        </View>

        <View style={[styles.list, { borderTopColor: colors.line }]}>
          {tasks.map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              active={task.id === activeId}
              onToggle={() => {
                setActiveId(task.id);
                toggleTask(task.id);
              }}
              onSkip={() => {
                setActiveId(task.id);
                skipTask(task.id);
              }}
            />
          ))}
        </View>

        {wide ? (
          <Text style={[styles.keys, { color: colors.inkMuted }]}>
            ↑ ↓ 移动 · 空格完成 · L 今天先不做
          </Text>
        ) : null}
      </View>

      <Text style={[styles.footnote, { color: colors.inkMuted, maxWidth: wide ? 560 : undefined }]}>
        今天先做这些，剩下的明天再说。已完成 <Text style={styles.mono}>{completedCount}</Text> 件。
      </Text>
    </View>
  );
}

function AddGoalBar({
  value,
  onChange,
  onSubmit,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
}) {
  const { colors } = useTheme();
  const [focused, setFocused] = useState(false);

  return (
    <View style={styles.addBar}>
      <TextInput
        value={value}
        onChangeText={onChange}
        onSubmitEditing={onSubmit}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder="输入新目标，按回车添加…"
        placeholderTextColor={colors.inkFaint}
        returnKeyType="done"
        accessibilityLabel="输入新目标"
        style={[
          styles.input,
          {
            color: colors.ink,
            borderColor: focused ? colors.lineStrong : colors.line,
            backgroundColor: colors.paper,
          },
        ]}
      />
      <Button label="添加" variant="primary" onPress={onSubmit} />
    </View>
  );
}

function NowCard({
  task,
  ruler,
  energyLabelText,
  onStart,
  onSkip,
}: {
  task: TaskRead;
  ruler: RulerSegment[];
  energyLabelText: string;
  onStart: () => void;
  onSkip: () => void;
}) {
  const { colors } = useTheme();

  return (
    <View style={[styles.card, { borderColor: colors.lineStrong, backgroundColor: colors.paper }]}>
      <View style={styles.cardHead}>
        <View style={styles.nowTag}>
          <View style={[styles.nowDot, { backgroundColor: colors.mint }]} />
          <Text style={[styles.nowText, { color: colors.ink }]}>现在</Text>
        </View>
        <Text style={[styles.cardTime, { color: colors.inkMuted }]}>
          {task.start_time ? `${hhmm(task.start_time)}–${hhmm(task.end_time)}` : '今天'}
        </Text>
      </View>

      <View style={styles.displayRow}>
        <Text style={[styles.display, { color: colors.ink }]}>
          {minutesLabel(task.estimated_duration)}
        </Text>
        <Text style={[styles.unit, { color: colors.inkMuted }]}>分钟</Text>
      </View>

      <Text style={[styles.taskTitle, { color: colors.ink }]}>{task.title}</Text>
      <Text style={[styles.taskMeta, { color: colors.inkMuted }]}>{energyLabelText}</Text>

      <Ruler segments={ruler} />

      <WhyNote text={mockWhyNow} />

      <View style={styles.actions}>
        <Button label="开始" variant="primary" onPress={onStart} />
        <Button label="今天先不做" variant="ghost" onPress={onSkip} />
      </View>
    </View>
  );
}

function TaskRow({
  task,
  active,
  onToggle,
  onSkip,
}: {
  task: TaskRead;
  active: boolean;
  onToggle: () => void;
  onSkip: () => void;
}) {
  const { colors } = useTheme();
  const { focused, hovered, handlers } = useInteraction();
  const done = task.status === 'completed' || task.status === 'skipped';
  const ringed = focused || active;

  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{ checked: done }}
      accessibilityLabel={task.title}
      onPress={onToggle}
      {...handlers}
      style={[
        styles.row,
        {
          borderBottomColor: colors.line,
          backgroundColor: hovered || active ? colors.hover : 'transparent',
          boxShadow: ringed ? `inset 0 0 0 2px ${colors.lineStrong}` : undefined,
        },
      ]}>
      <View
        style={[
          styles.checkbox,
          { borderColor: colors.ink, backgroundColor: done ? colors.ink : 'transparent' },
        ]}>
        {done ? <Text style={[styles.checkGlyph, { color: colors.onInk }]}>✓</Text> : null}
      </View>

      <Text
        style={[
          styles.rowTitle,
          {
            color: done ? colors.inkMuted : colors.ink,
            textDecorationLine: done ? 'line-through' : 'none',
          },
        ]}>
        {task.title}
      </Text>

      {hovered && !done ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`今天先不做：${task.title}`}
          onPress={(event) => {
            event.stopPropagation?.();
            onSkip();
          }}
          style={styles.rowAction}>
          <Text style={[styles.rowActionText, { color: colors.mintInk }]}>今天先不做</Text>
        </Pressable>
      ) : null}

      <Text style={[styles.rowDuration, { color: colors.inkMuted }]}>
        {minutesLabel(task.estimated_duration)}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: Space.xxl,
  },
  mono: {
    fontFamily: 'IBMPlexMono_500Medium',
  },
  addBar: {
    flexDirection: 'row',
    gap: Space.sm,
    alignItems: 'stretch',
  },
  input: {
    flex: 1,
    minHeight: 44,
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: Space.md,
    fontSize: Type.body,
  },
  card: {
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: Space.xl,
    gap: Space.lg,
  },
  cardHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  nowTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  nowDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  nowText: {
    fontSize: Type.small,
    fontWeight: '700',
    letterSpacing: 1,
  },
  cardTime: {
    fontSize: Type.small,
    fontFamily: 'IBMPlexMono_400Regular',
  },
  displayRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Space.sm,
  },
  display: {
    fontSize: Type.display,
    lineHeight: Type.display * 0.95,
    fontFamily: 'IBMPlexMono_500Medium',
  },
  unit: {
    fontSize: Type.unit,
    lineHeight: Type.unit * 1.2,
    paddingBottom: 10,
  },
  taskTitle: {
    fontSize: Type.heading,
    fontWeight: '700',
    lineHeight: Type.heading * Line.tight,
  },
  taskMeta: {
    fontSize: Type.body,
    lineHeight: Type.body * Line.normal,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
    flexWrap: 'wrap',
  },
  section: {
    gap: Space.md,
  },
  sectionHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  sectionTitle: {
    fontSize: Type.title,
    fontWeight: '700',
  },
  sectionMeta: {
    fontSize: Type.small,
  },
  list: {
    borderTopWidth: 1,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    minHeight: 56,
    paddingVertical: Space.md,
    borderBottomWidth: 1,
  },
  checkbox: {
    width: 20,
    height: 20,
    borderRadius: Radius.sm,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkGlyph: {
    fontSize: Type.small,
    lineHeight: Type.small * 1.1,
    fontWeight: '700',
  },
  rowTitle: {
    flex: 1,
    fontSize: Type.body,
    lineHeight: Type.body * Line.normal,
  },
  rowAction: {
    paddingHorizontal: Space.sm,
    minHeight: 32,
    justifyContent: 'center',
  },
  rowActionText: {
    fontSize: Type.small,
  },
  rowDuration: {
    fontSize: Type.small,
    fontFamily: 'IBMPlexMono_400Regular',
    minWidth: 28,
    textAlign: 'right',
  },
  keys: {
    fontSize: Type.small,
  },
  footnote: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.relaxed,
  },
});
