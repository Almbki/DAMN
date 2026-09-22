import { useRouter } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { StyleSheet, Text, View, useWindowDimensions } from 'react-native';

import { DailyFeedbackSheet } from '@/components/daily-feedback-sheet';
import { PlanChangeSheet } from '@/components/plan-change-sheet';
import { TaskEditor } from '@/components/task-editor';
import { TaskRow } from '@/components/task-row';
import { Timeline, type TimelineItem } from '@/components/timeline';
import { Button } from '@/components/ui/button';
import { FilterChip } from '@/components/ui/chip';
import { Segmented } from '@/components/ui/segmented';
import { EmptyState } from '@/components/ui/states';
import { Fonts, Layout, Line, Space, Type } from '@/constants/tokens';
import { formatShort, parseISO, todayISO } from '@/domain/date';
import { groupByGoal, weekDates } from '@/domain/selectors';
import { isClosed, type Task } from '@/domain/task';
import { useListKeys } from '@/hooks/use-list-keys';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

const VIEWS = ['今日', '本周', '每月'];
const FILTERS = ['全部', '未完成'];
const WEEKDAY = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

function toItem(task: Task): TimelineItem {
  return {
    id: task.id,
    title: task.title,
    done: isClosed(task),
    startTime: task.startTime,
    endTime: task.endTime,
    estimatedMinutes: task.estimatedMinutes,
    priority: task.priority,
  };
}

export default function TodoScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const wide = width > 0 && width >= Layout.breakpoint;
  const {
    tasks,
    lists,
    currentTask,
    stats,
    mode,
    canEditTasks,
    goals,
    planChanges,
    updateTask,
    deleteTask,
    toggleDone,
    setSkipped,
    moveBy,
    replanNow,
  } = usePlan();
  const isApi = mode === 'api';

  const [view, setView] = useState(0);
  const [filter, setFilter] = useState(1);
  const [grouped, setGrouped] = useState(false);
  const [changeOpen, setChangeOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [replanBusy, setReplanBusy] = useState(false);
  const [replanMessage, setReplanMessage] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  const handleReplan = useCallback(async () => {
    setReplanBusy(true);
    try {
      setReplanMessage(await replanNow());
    } finally {
      setReplanBusy(false);
    }
  }, [replanNow]);

  const today = todayISO();
  const openOnly = filter === 1;
  const applyFilter = useCallback(
    (items: Task[]) => (openOnly ? items.filter((task) => !isClosed(task)) : items),
    [openOnly],
  );

  const todayTasks = useMemo(() => applyFilter(lists.today), [applyFilter, lists.today]);
  const overdueTasks = useMemo(
    () => applyFilter(tasks.filter((task) => task.dueDate != null && task.dueDate < today)),
    [applyFilter, tasks, today],
  );
  const groupedTasks = useMemo(
    () => groupByGoal(todayTasks, goals).filter((group) => group.tasks.length > 0),
    [todayTasks, goals],
  );
  const week = useMemo(
    () =>
      weekDates(today).map((date) => ({
        date,
        tasks: applyFilter(tasks.filter((task) => task.dueDate === date)),
      })),
    [applyFilter, tasks, today],
  );

  const editingTask = editingId == null ? null : (tasks.find((task) => task.id === editingId) ?? null);

  const move = useCallback(
    (delta: number) => {
      if (todayTasks.length === 0) return;
      setActiveId((current) => {
        const fromId = current ?? currentTask?.id ?? todayTasks[0].id;
        const index = todayTasks.findIndex((task) => task.id === fromId);
        const next = Math.min(todayTasks.length - 1, Math.max(0, index + delta));
        return todayTasks[next].id;
      });
    },
    [todayTasks, currentTask],
  );
  const toggleActive = useCallback(() => {
    const id = activeId ?? currentTask?.id ?? todayTasks[0]?.id;
    if (id == null) return;
    setActiveId(id);
    toggleDone(id);
  }, [activeId, currentTask, todayTasks, toggleDone]);
  const skipActive = useCallback(() => {
    const id = activeId ?? currentTask?.id ?? todayTasks[0]?.id;
    if (id == null) return;
    setActiveId(id);
    setSkipped(id, true);
  }, [activeId, currentTask, todayTasks, setSkipped]);
  useListKeys({
    onPrev: () => move(-1),
    onNext: () => move(1),
    onToggle: toggleActive,
    onSkip: skipActive,
  });

  function renderTimeline(items: Task[]) {
    return (
      <Timeline
        items={items.map(toItem)}
        nowId={currentTask?.id ?? null}
        activeId={activeId}
        onToggleDone={toggleDone}
        onOpen={canEditTasks ? (id) => setEditingId(id) : undefined}
        onSkip={(id) => setSkipped(id, true)}
      />
    );
  }

  function renderRow(task: Task) {
    return (
      <TaskRow
        key={task.id}
        task={task}
        active={task.id === activeId}
        onToggleDone={() => toggleDone(task.id)}
        onOpen={canEditTasks ? () => setEditingId(task.id) : undefined}
        onSkip={() => setSkipped(task.id, true)}
      />
    );
  }

  return (
    <View style={styles.page}>
      <View style={styles.controls}>
        <View style={styles.controlsRow}>
          <View style={styles.viewSwitch}>
            <Segmented options={VIEWS} value={view} onChange={setView} />
          </View>
          <Button
            label={planChanges.length > 0 ? `计划变更 · ${planChanges.length}` : '计划变更'}
            variant="tonal"
            icon="calendar"
            onPress={() => setChangeOpen(true)}
          />
        </View>

        <View style={styles.filterRow}>
          <View style={styles.filterSwitch}>
            <Segmented options={FILTERS} value={filter} onChange={setFilter} size="sm" />
          </View>
          <FilterChip
            label="按分组"
            icon="swap"
            selected={grouped}
            onPress={() => setGrouped((value) => !value)}
          />
          <Button
            label={replanBusy ? '重排中…' : '重排计划'}
            variant="outlined"
            icon="swap"
            disabled={replanBusy}
            onPress={() => {
              void handleReplan();
            }}
          />
        </View>
        {replanMessage ? (
          <Text style={[styles.replanNote, { color: colors.inkMuted }]}>{replanMessage}</Text>
        ) : null}
      </View>

      {view === 0 ? (
        <View style={styles.list}>
          {overdueTasks.length > 0 ? (
            <View style={styles.group}>
              <Text style={[styles.groupTitle, { color: colors.error }]}>
                已逾期 · {overdueTasks.length}
              </Text>
              {renderTimeline(overdueTasks)}
            </View>
          ) : null}

          {todayTasks.length > 0 ? (
            grouped ? (
              groupedTasks.map((group) => (
                <View key={group.goal?.id ?? 'none'} style={styles.group}>
                  <Text style={[styles.groupTitle, { color: colors.inkMuted }]}>
                    {group.goal?.title ?? '未归入目标'}
                  </Text>
                  {renderTimeline(group.tasks)}
                </View>
              ))
            ) : (
              <View style={styles.group}>
                {overdueTasks.length > 0 ? (
                  <Text style={[styles.groupTitle, { color: colors.inkMuted }]}>今天</Text>
                ) : null}
                {renderTimeline(todayTasks)}
              </View>
            )
          ) : null}

          {todayTasks.length === 0 && overdueTasks.length === 0 ? (
            <EmptyState
              title={isApi ? '今天没有排任务' : '今天没有安排'}
              body={
                isApi
                  ? '去「目标」写一个目标，系统会把它拆成今天能做的事。'
                  : '去「目标」写下一个目标，系统会把它拆成今天能做完的几步。'
              }
              actionLabel="去添加目标"
              actionIcon="plus"
              onAction={() => router.push('/goal')}
            />
          ) : null}
        </View>
      ) : null}

      {view === 1 ? (
        <View style={styles.week}>
          {week.map((day) => {
            const isToday = day.date === today;
            const weekday = WEEKDAY[parseISO(day.date).getDay()];
            return (
              <View key={day.date} style={styles.dayBlock}>
                <View style={styles.dayHead}>
                  <Text style={[styles.dayName, { color: isToday ? colors.primary : colors.ink }]}>
                    {isToday ? `今天 · ${weekday}` : weekday}
                  </Text>
                  <Text style={[styles.dayDate, { color: colors.inkFaint }]}>
                    {formatShort(day.date)}
                  </Text>
                </View>
                {day.tasks.length > 0 ? (
                  day.tasks.map(renderRow)
                ) : (
                  <Text
                    style={[
                      styles.dayEmpty,
                      { color: colors.inkFaint, borderBottomColor: colors.outlineVariant },
                    ]}>
                    无任务
                  </Text>
                )}
              </View>
            );
          })}
        </View>
      ) : null}

      {view === 2 ? (
        <EmptyState
          title="月视图还要等后端"
          body="现在计划只排到未来约 14 天，按月聚合没有数据可看。等后端支持更长周期（或跨版本查询）后再打开这里。"
          actionLabel="回到今日"
          onAction={() => setView(0)}
        />
      ) : null}

      <View style={[styles.footer, { borderTopColor: colors.outlineVariant }]}>
        <Text style={[styles.footnote, { color: colors.inkMuted }]}>
          共 <Text style={styles.mono}>{stats.openCount}</Text> 件未完成 · 已完成{' '}
          <Text style={styles.mono}>{stats.completedToday}</Text> 件 · 连续{' '}
          <Text style={styles.mono}>{stats.streak}</Text> 天
        </Text>
        <Button label="写今日反馈" variant="filled" onPress={() => setFeedbackOpen(true)} />
      </View>

      {wide && view === 0 ? (
        <Text style={[styles.keys, { color: colors.inkMuted }]}>
          ↑ ↓ 移动 · 空格完成 · L 今天先不做
        </Text>
      ) : null}

      <PlanChangeSheet
        visible={changeOpen}
        changes={planChanges}
        onClose={() => setChangeOpen(false)}
      />
      <DailyFeedbackSheet visible={feedbackOpen} onClose={() => setFeedbackOpen(false)} />

      {canEditTasks && editingTask ? (
        <TaskEditor
          key={editingTask.id}
          task={editingTask}
          isNew={false}
          onClose={() => setEditingId(null)}
          onSave={(id, patch) => updateTask(id, patch)}
          onDelete={deleteTask}
          onMove={moveBy}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: Space.xl,
  },
  controls: {
    gap: Space.md,
  },
  controlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  viewSwitch: {
    flex: 1,
    maxWidth: 360,
  },
  filterRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
  },
  filterSwitch: {
    flex: 1,
    maxWidth: 220,
  },
  replanNote: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  list: {
    gap: Space.xl,
  },
  group: {
    gap: Space.sm,
  },
  groupTitle: {
    fontSize: Type.labelLarge,
    fontWeight: '600',
  },
  week: {
    gap: Space.xl,
  },
  dayBlock: {
    gap: Space.xs,
  },
  dayHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  dayName: {
    fontSize: Type.titleMedium,
    fontWeight: '600',
  },
  dayDate: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
  dayEmpty: {
    fontSize: Type.bodyMedium,
    paddingVertical: Space.md,
    borderBottomWidth: 1,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: Space.md,
    borderTopWidth: 1,
    paddingTop: Space.lg,
  },
  footnote: {
    fontSize: Type.bodyMedium,
    lineHeight: Type.bodyMedium * Line.relaxed,
  },
  mono: {
    fontFamily: Fonts.mono,
  },
  keys: {
    fontSize: Type.labelMedium,
  },
});
