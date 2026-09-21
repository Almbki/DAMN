import { useMemo, useState } from 'react';
import {
  Animated,
  Easing as RNEasing,
  Pressable,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';

import { FocusTimer } from '@/components/focus-timer';
import { useHeaderControls } from '@/components/shell/header-controls';
import { Surface } from '@/components/surface';
import { Button } from '@/components/ui/button';
import { useInteraction } from '@/components/ui/interaction';
import { useRipple } from '@/components/ui/ripple';
import { Segmented } from '@/components/ui/segmented';
import {
  Duration,
  Fonts,
  Line,
  Motion,
  PressScale,
  Radius,
  RingWidth,
  Space,
  Type,
} from '@/constants/tokens';
import { mockPlanChanges } from '@/data/mock';
import { addDays, formatShort, parseISO, todayISO } from '@/domain/date';
import { isClosed, type Task } from '@/domain/task';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

const VIEWS = ['今日', '本周', '每月'] as const;
const ENERGY = ['偏低', '一般', '不错', '很好'] as const;
const STRESS = ['很低', '中等', '偏高', '很高'] as const;
const MOOD = ['低落', '平静', '轻松', '愉快'] as const;
const WEEKDAY = ['日', '一', '二', '三', '四', '五', '六'];

function inView(task: Task, view: number, today: string): boolean {
  if (!task.dueDate) return view === 0;
  if (view === 0) return task.dueDate === today;
  if (view === 1) return task.dueDate >= today && task.dueDate <= addDays(today, 6);
  return task.dueDate >= today && task.dueDate <= addDays(today, 29);
}

type Group = { key: string; label: string; tasks: Task[] };

/** Explicit buckets — no wrapping, no dependency on list order. */
function groupByTime(tasks: Task[]): Group[] {
  const buckets: Record<string, Task[]> = { morning: [], afternoon: [], evening: [], any: [] };
  tasks.forEach((task) => {
    const hour = task.dueTime ? Number(task.dueTime.slice(0, 2)) : -1;
    if (hour < 0 || hour >= 24) buckets.any.push(task);
    else if (hour < 12) buckets.morning.push(task);
    else if (hour < 18) buckets.afternoon.push(task);
    else buckets.evening.push(task);
  });
  return [
    { key: 'morning', label: '上午', tasks: buckets.morning },
    { key: 'afternoon', label: '下午', tasks: buckets.afternoon },
    { key: 'evening', label: '晚上', tasks: buckets.evening },
    { key: 'any', label: '未排时间', tasks: buckets.any },
  ].filter((group) => group.tasks.length > 0);
}

export default function TodoScreen() {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const { tasks, toggleDone, logFocus } = usePlan();
  const today = todayISO();

  const [view, setView] = useState(0);
  const [openOnly, setOpenOnly] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [changeOpen, setChangeOpen] = useState(false);
  const [energy, setEnergy] = useState(1);
  const [stress, setStress] = useState(1);
  const [mood, setMood] = useState(1);
  const [feedbackDone, setFeedbackDone] = useState(false);

  const inViewTasks = useMemo(
    () =>
      tasks
        .filter((task) => inView(task, view, today))
        .sort((a, b) => a.order - b.order),
    [tasks, view, today],
  );

  const visible = openOnly ? inViewTasks.filter((task) => !isClosed(task)) : inViewTasks;
  const groups = useMemo(() => groupByTime(visible), [visible]);
  const sheetWidth = Math.min(340, Math.max(240, width - 32));

  // The two controls live in the shell header. The memo keeps the registered
  // nodes stable across unrelated re-renders so the header only updates when it
  // should; the "今日/本周/每月" segmented control stays in the page content.
  const headerControls = useMemo(
    () => ({
      left: (
        <ToolbarButton
          label={openOnly ? '只看未完成' : '按分组'}
          hint={openOnly ? '切换为按分组' : '切换为只看未完成'}
          onPress={() => setOpenOnly((value) => !value)}
        />
      ),
      right: (
        <ToolbarButton
          label={`${mockPlanChanges.length} 处调整`}
          hint="查看计划变更"
          marker
          onPress={() => setChangeOpen((value) => !value)}
        />
      ),
    }),
    [openOnly],
  );

  useHeaderControls(headerControls);

  return (
    <View style={styles.page}>
      {changeOpen ? (
        <Surface elevation="overlay" radius={Radius.lg} style={[styles.sheet, { width: sheetWidth }]}>
          <Text style={[styles.sectionTitle, { color: colors.ink }]}>计划有调整</Text>
          <Text style={[styles.sheetHint, { color: colors.inkMuted }]}>
            系统改动了未来几天，点一下就能看到。
          </Text>
          {mockPlanChanges.map((change) => (
            <View key={change.id} style={[styles.changeRow, { borderTopColor: colors.line }]}>
              <Text style={[styles.changeDate, { color: colors.inkMuted }]}>
                {formatShort(change.date)} 周{WEEKDAY[parseISO(change.date).getDay()]}
              </Text>
              <Text style={[styles.changeText, { color: colors.ink }]}>{change.text}</Text>
            </View>
          ))}
          <Button label="知道了" variant="ghost" onPress={() => setChangeOpen(false)} />
        </Surface>
      ) : null}

      <Segmented
        options={VIEWS}
        value={view}
        onChange={(index) => {
          setView(index);
          setExpandedId(null);
        }}
      />

      {openOnly ? (
        <View style={styles.list}>
          {visible.length === 0 ? (
            <Text style={[styles.empty, { color: colors.inkMuted }]}>这个范围没有未完成的任务。</Text>
          ) : (
            visible.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                active={expandedId === task.id}
                animateExit={openOnly}
                onToggleDone={() => toggleDone(task.id)}
                onToggleExpand={() => setExpandedId((id) => (id === task.id ? null : task.id))}
                onLog={(minutes) => logFocus(task.id, minutes)}
              />
            ))
          )}
        </View>
      ) : groups.length === 0 ? (
        <Text style={[styles.empty, { color: colors.inkMuted }]}>这个范围没有任务。</Text>
      ) : (
        groups.map((group) => (
          <View key={group.key} style={styles.group}>
            <Text style={[styles.groupLabel, { color: colors.inkMuted }]}>
              {group.label} · {group.tasks.length}
            </Text>
            <View style={styles.list}>
              {group.tasks.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  active={expandedId === task.id}
                  animateExit={false}
                  onToggleDone={() => toggleDone(task.id)}
                  onToggleExpand={() => setExpandedId((id) => (id === task.id ? null : task.id))}
                  onLog={(minutes) => logFocus(task.id, minutes)}
                />
              ))}
            </View>
          </View>
        ))
      )}

      <Surface elevation="raised" radius={Radius.lg} style={styles.feedback}>
        <Text style={[styles.sectionTitle, { color: colors.ink }]}>今天感觉怎么样</Text>
        <Segmented label="精力" options={ENERGY} value={energy} onChange={setEnergy} />
        <Segmented label="压力" options={STRESS} value={stress} onChange={setStress} />
        <Segmented label="心情" options={MOOD} value={mood} onChange={setMood} />
        {feedbackDone ? (
          <Text style={[styles.feedbackNote, { color: colors.ink }]}>
            已记录 · 精力 {ENERGY[energy]} · 压力 {STRESS[stress]} · 心情 {MOOD[mood]}
          </Text>
        ) : (
          <Button label="提交反馈" variant="primary" onPress={() => setFeedbackDone(true)} />
        )}
      </Surface>
    </View>
  );
}

function ToolbarButton({
  label,
  hint,
  marker = false,
  onPress,
}: {
  label: string;
  hint: string;
  marker?: boolean;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const { focused, hovered, handlers } = useInteraction();
  const ripple = useRipple(colors.ripple);

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${label}，${hint}`}
      onPress={onPress}
      {...handlers}
      onLayout={ripple.onLayout}
      onPressIn={ripple.onPressIn}
      style={({ pressed }) => [
        styles.toolbarBtn,
        {
          borderColor: colors.line,
          backgroundColor: pressed ? colors.pressed : hovered ? colors.hover : 'transparent',
          transform: pressed && !reduced ? [{ scale: PressScale }] : undefined,
        },
      ]}>
      {ripple.node}
      {marker ? <View style={[styles.dot, { backgroundColor: colors.accent }]} /> : null}
      <Text style={[styles.toolbarText, { color: colors.ink }]}>{label}</Text>
      {focused ? (
        <View
          pointerEvents="none"
          style={[styles.ring, styles.ringSm, { borderColor: colors.accent }]}
        />
      ) : null}
    </Pressable>
  );
}

function TaskRow({
  task,
  active,
  animateExit,
  onToggleDone,
  onToggleExpand,
  onLog,
}: {
  task: Task;
  active: boolean;
  /** True when completing the task removes the row; hold it for the exit. */
  animateExit: boolean;
  onToggleDone: () => void;
  onToggleExpand: () => void;
  onLog: (minutes: number) => void;
}) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const check = useInteraction();
  const body = useInteraction();
  const checkRipple = useRipple(colors.ripple);
  const bodyRipple = useRipple(colors.ripple);
  const done = task.done;

  // Completing a task makes its row leave the list; hold it for 300ms so the
  // exit reads as a movement instead of a jump. A lazy state value, not a ref:
  // the animated value is read during render.
  const [exit] = useState(() => new Animated.Value(1));
  const [exiting, setExiting] = useState(false);

  function handleToggleDone() {
    if (!done && animateExit && !reduced) {
      setExiting(true);
      Animated.timing(exit, {
        toValue: 0,
        duration: Duration.medium,
        easing: RNEasing.bezier(0.3, 0, 0.8, 0.15),
        useNativeDriver: Motion.nativeDriver,
      }).start(() => onToggleDone());
      return;
    }
    onToggleDone();
  }

  const marked = done || exiting;

  return (
    <Animated.View
      style={[
        styles.rowWrap,
        {
          opacity: exit,
          transform: [
            { translateY: exit.interpolate({ inputRange: [0, 1], outputRange: [-8, 0] }) },
          ],
        },
      ]}>
      <View style={[styles.row, { borderBottomColor: colors.line, borderLeftColor: active ? colors.accent : 'transparent' }]}>
        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked: marked }}
          accessibilityLabel={`${done ? '取消完成' : '完成'}：${task.title}`}
          onPress={handleToggleDone}
          {...check.handlers}
          onLayout={checkRipple.onLayout}
          onPressIn={checkRipple.onPressIn}
          style={styles.checkHit}>
          {checkRipple.node}
          <View
            style={[
              styles.circle,
              {
                borderColor: marked ? colors.ink : colors.inkMuted,
                backgroundColor: marked ? colors.ink : 'transparent',
              },
            ]}>
            {marked ? <Text style={[styles.checkGlyph, { color: colors.onAccent }]}>✓</Text> : null}
          </View>
          {check.focused ? (
            <View
              pointerEvents="none"
              style={[styles.ring, { borderColor: colors.accent, borderRadius: Radius.full }]}
            />
          ) : null}
        </Pressable>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`${task.title}，${active ? '收起专注计时' : '展开专注计时'}`}
          onPress={onToggleExpand}
          {...body.handlers}
          onLayout={bodyRipple.onLayout}
          onPressIn={bodyRipple.onPressIn}
          style={({ pressed }) => [
            styles.rowBody,
            {
              transform: pressed && !reduced ? [{ scale: PressScale }] : undefined,
            },
          ]}>
          {bodyRipple.node}
          <View style={styles.rowText}>
            <Text
              style={[
                styles.taskTitle,
                { color: colors.ink, opacity: marked ? 0.6 : 1, textDecorationLine: marked ? 'line-through' : 'none' },
              ]}>
              {task.title}
            </Text>
            <Text style={[styles.taskMeta, { color: colors.inkMuted }]}>
              {task.dueTime ? `${task.dueTime} · ` : ''}
              {active ? '专注计时中' : '点开开始专注'}
            </Text>
          </View>
          <View style={styles.duration}>
            <Text style={[styles.durationNum, { color: colors.ink, opacity: marked ? 0.6 : 1 }]}>
              {task.estimatedMinutes ?? '—'}
            </Text>
            <Text style={[styles.durationUnit, { color: colors.inkMuted }]}>分</Text>
          </View>
          {body.focused ? (
            <View
              pointerEvents="none"
              style={[styles.ring, { borderColor: colors.accent, borderRadius: Radius.sm }]}
            />
          ) : null}
        </Pressable>
      </View>

      {active ? (
        <View style={styles.timerSlot}>
          <FocusTimer task={task} onLog={onLog} />
        </View>
      ) : null}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: Space.lg,
  },
  toolbarBtn: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
    paddingHorizontal: Space.lg,
    borderWidth: 1,
    borderRadius: Radius.full,
    overflow: 'hidden',
  },
  toolbarText: {
    fontSize: Type.small,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  sheet: {
    position: 'absolute',
    top: Space.sm,
    right: 0,
    zIndex: 20,
    padding: Space.lg,
    gap: Space.sm,
  },
  sheetHint: {
    fontSize: Type.small,
    lineHeight: Type.small * Line.relaxed,
  },
  changeRow: {
    borderTopWidth: 1,
    paddingTop: Space.sm,
    gap: 2,
  },
  changeDate: {
    fontSize: Type.small,
    fontFamily: Fonts.mono,
  },
  changeText: {
    fontSize: Type.body,
    lineHeight: Type.body * Line.normal,
  },
  group: {
    gap: Space.sm,
  },
  groupLabel: {
    fontSize: Type.small,
  },
  list: {
    width: '100%',
  },
  empty: {
    fontSize: Type.body,
    paddingVertical: Space.lg,
  },
  rowWrap: {
    width: '100%',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderLeftWidth: 3,
  },
  checkHit: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  circle: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkGlyph: {
    fontSize: 14,
    lineHeight: 16,
  },
  rowBody: {
    flex: 1,
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
    paddingVertical: Space.sm,
    paddingRight: Space.xs,
    overflow: 'hidden',
  },
  rowText: {
    flex: 1,
    gap: 2,
  },
  taskTitle: {
    fontSize: Type.bodyLg,
    fontWeight: '700',
    lineHeight: Type.bodyLg * Line.tight,
  },
  taskMeta: {
    fontSize: Type.small,
  },
  duration: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 2,
  },
  durationNum: {
    fontSize: Type.heading,
    lineHeight: Type.heading,
    fontFamily: Fonts.mono,
  },
  durationUnit: {
    fontSize: Type.micro,
    paddingBottom: 3,
  },
  timerSlot: {
    paddingVertical: Space.md,
  },
  sectionTitle: {
    fontSize: Type.title,
    fontWeight: '700',
  },
  feedback: {
    padding: Space.lg,
    gap: Space.md,
  },
  feedbackNote: {
    fontSize: Type.body,
    lineHeight: Type.body * Line.normal,
  },
  ring: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderWidth: RingWidth,
  },
  ringSm: {
    borderRadius: Radius.full,
  },
});
