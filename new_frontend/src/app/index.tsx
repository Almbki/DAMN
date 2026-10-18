import { useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { StyleSheet, Text, View, useWindowDimensions } from 'react-native';

import { PlanChangeSheet } from '@/components/plan-change-sheet';
import { ScheduleSection } from '@/components/schedule/schedule-section';
import { TaskRow } from '@/components/task-row';
import { Banner } from '@/components/task/banner';
import { QuickTaskDialog } from '@/components/task/quick-task-dialog';
import { TaskDetailSheet } from '@/components/task/task-detail-sheet';
import { TaskFilterChip } from '@/components/task/task-filter-chip';
import { Timeline, type TimelineItem } from '@/components/timeline';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Segmented } from '@/components/ui/segmented';
import { EmptyState } from '@/components/ui/states';
import { Fonts, Layout, Line, Radius, Space, Type } from '@/constants/tokens';
import { formatShort, parseISO, todayISO } from '@/domain/date';
import { groupByGoal, weekDates } from '@/domain/selectors';
import { isClosed, type Task } from '@/domain/task';
import { useListKeys } from '@/hooks/use-list-keys';
import { usePlan } from '@/state/plan';
import { useTheme } from '@/state/theme';

type FilterKey = 'all' | 'open' | 'done';

const VIEWS = ['今日', '本周', '每月'];
const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'open', label: '未完成' },
  { key: 'done', label: '已完成' },
];
const WEEKDAY = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

function toItem(task: Task): TimelineItem {
  return {
    id: task.id,
    title: task.title,
    done: task.done,
    skipped: task.skipped,
    startTime: task.startTime,
    endTime: task.endTime,
    estimatedMinutes: task.estimatedMinutes,
    priority: task.priority,
    taskKind: task.taskKind,
    seriesIndex: task.seriesIndex,
    occurrenceDate: task.occurrenceDate,
  };
}

function timeValue(task: Task): string {
  return task.startTime ?? task.dueTime ?? '99:99';
}

function byStartTime(a: Task, b: Task): number {
  return timeValue(a).localeCompare(timeValue(b)) || a.order - b.order;
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
    canCreateTasks,
    actionError,
    clearActionError,
    goals,
    planChanges,
    updateTask,
    updateStandard,
    setDone,
    setSkipped,
    moveBy,
    replanNow,
    createTask,
    deleteTask,
  } = usePlan();
  const isApi = mode === 'api';

  const [view, setView] = useState(0);
  const [filter, setFilter] = useState<FilterKey>('open');
  const [grouped, setGrouped] = useState(false);
  const [changeOpen, setChangeOpen] = useState(false);
  const [replanBusy, setReplanBusy] = useState(false);
  const [replanMessage, setReplanMessage] = useState<string | null>(null);
  const [replanConfirmOpen, setReplanConfirmOpen] = useState(false);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [deleteNotice, setDeleteNotice] = useState<{ id: number; title: string } | null>(null);
  const [undo, setUndo] = useState<{ id: number; title: string } | null>(null);
  const undoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [addHintOpen, setAddHintOpen] = useState(false);
  const [quickAddOpen, setQuickAddOpen] = useState(false);
  const [scheduleOverlayOpen, setScheduleOverlayOpen] = useState(false);

  const dismissUndo = useCallback(() => {
    if (undoTimer.current) {
      clearTimeout(undoTimer.current);
      undoTimer.current = null;
    }
    setUndo(null);
  }, []);

  useEffect(
    () => () => {
      if (undoTimer.current) clearTimeout(undoTimer.current);
    },
    [],
  );

  const showUndo = useCallback((task: Pick<Task, 'id' | 'title'>) => {
    if (undoTimer.current) clearTimeout(undoTimer.current);
    setUndo({ id: task.id, title: task.title });
    undoTimer.current = setTimeout(() => {
      undoTimer.current = null;
      setUndo(null);
    }, 5000);
  }, []);

  const handleToggleById = useCallback(
    (id: number) => {
      const task = tasks.find((item) => item.id === id);
      if (!task) return;
      if (task.done) {
        setDone(id, false);
        return;
      }
      setDone(id, true);
      showUndo(task);
    },
    [tasks, setDone, showUndo],
  );

  const undoCompletion = useCallback(() => {
    if (!undo) return;
    setDone(undo.id, false);
    dismissUndo();
  }, [undo, setDone, dismissUndo]);

  const handleOpen = useCallback((id: number) => {
    setDetailId(id);
  }, []);

  // The confirmation lives on this screen: the sheet asks, we close it, and the
  // dialog is the only modal in the tree while the user decides.
  const requestDelete = useCallback((id: number) => {
    setDeleteTargetId(id);
    setDetailId(null);
  }, []);

  const confirmDelete = useCallback(() => {
    if (deleteTargetId == null) return;
    const task = tasks.find((item) => item.id === deleteTargetId) ?? null;
    if (!task) {
      setDeleteTargetId(null);
      return;
    }
    clearActionError();
    deleteTask(task.id);
    setDetailId(null);
    setActiveId(null);
    setDeleteTargetId(null);
    setDeleteNotice({ id: task.id, title: task.title });
  }, [deleteTargetId, tasks, deleteTask, clearActionError]);

  const goGoal = useCallback(() => {
    setAddHintOpen(false);
    router.push('/goal');
  }, [router]);

  const handleAdd = useCallback(() => {
    if (canCreateTasks) {
      setQuickAddOpen(true);
      return;
    }
    setAddHintOpen(true);
  }, [canCreateTasks]);

  const runReplan = useCallback(async () => {
    setReplanConfirmOpen(false);
    setReplanBusy(true);
    setReplanMessage(null);
    dismissUndo();
    try {
      setReplanMessage(await replanNow());
    } catch {
      setReplanMessage('重排没有完成，请稍后再试。');
    } finally {
      setReplanBusy(false);
    }
  }, [replanNow, dismissUndo]);

  const today = todayISO();
  const allToday = lists.today;

  const openTodayCount = useMemo(
    () => allToday.filter((task) => !isClosed(task)).length,
    [allToday],
  );
  const doneTodayCount = useMemo(
    () => allToday.filter((task) => task.done).length,
    [allToday],
  );
  const skippedTodayCount = useMemo(
    () => allToday.filter((task) => task.skipped).length,
    [allToday],
  );

  const filterTasks = useCallback((items: Task[], key: FilterKey) => {
    if (key === 'open') return items.filter((task) => !isClosed(task));
    if (key === 'done') return items.filter((task) => task.done);
    return items;
  }, []);

  const todayTasks = useMemo(() => filterTasks(allToday, filter), [allToday, filter, filterTasks]);
  const overdueAll = useMemo(
    () => tasks.filter((task) => task.dueDate != null && task.dueDate < today),
    [tasks, today],
  );
  const overdueTasks = useMemo(
    () => filterTasks(overdueAll, filter),
    [overdueAll, filter, filterTasks],
  );
  const groupedTasks = useMemo(
    () => groupByGoal(todayTasks, goals).filter((group) => group.tasks.length > 0),
    [todayTasks, goals],
  );
  const week = useMemo(
    () =>
      weekDates(today).map((date) => ({
        date,
        tasks: filterTasks(
          tasks.filter((task) => task.dueDate === date),
          filter,
        ).sort(byStartTime),
      })),
    [tasks, today, filter, filterTasks],
  );

  const detailTask = detailId == null ? null : (tasks.find((task) => task.id === detailId) ?? null);
  const deleteTargetTask =
    deleteTargetId == null ? null : (tasks.find((task) => task.id === deleteTargetId) ?? null);

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
    handleToggleById(id);
  }, [activeId, currentTask, todayTasks, handleToggleById]);

  const deferActive = useCallback(() => {
    const id = activeId ?? currentTask?.id ?? todayTasks[0]?.id;
    if (id == null) return;
    setActiveId(id);
    moveBy(id, 1);
  }, [activeId, currentTask, todayTasks, moveBy]);

  const keysEnabled =
    view === 0 &&
    detailTask == null &&
    !changeOpen &&
    !addHintOpen &&
    !quickAddOpen &&
    !replanConfirmOpen &&
    deleteTargetId == null &&
    !scheduleOverlayOpen;

  useListKeys(
    {
      onPrev: () => move(-1),
      onNext: () => move(1),
      onToggle: toggleActive,
      onSkip: deferActive,
    },
    keysEnabled,
  );

  function renderTimeline(items: Task[]) {
    return (
      <Timeline
        items={items.map(toItem)}
        nowId={currentTask?.id ?? null}
        activeId={activeId}
        onToggleDone={handleToggleById}
        onOpen={handleOpen}
      />
    );
  }

  function renderRow(task: Task) {
    return (
      <TaskRow
        key={task.id}
        task={task}
        active={task.id === activeId}
        onToggleDone={() => handleToggleById(task.id)}
        onOpen={() => handleOpen(task.id)}
      />
    );
  }

  function renderEmpty() {
    if (!allToday.length) {
      return (
        <EmptyState
          title="今天没有排任务"
          body={
            isApi
              ? '去「目标」写一个目标，系统会把它拆成今天能做的事。'
              : '去「目标」写下一个目标，系统会把它拆成今天能做完的几步。'
          }
          actionLabel="去目标页"
          actionIcon="target"
          onAction={goGoal}
        />
      );
    }

    if (openTodayCount === 0) {
      const allSkipped = doneTodayCount === 0 && skippedTodayCount > 0;
      return (
        <EmptyState
          title={allSkipped ? '今天的任务都跳过了' : '今天全部完成'}
          body={
            allSkipped
              ? '今天安排的任务都被跳过了。想重新安排，去目标页写下新的目标。'
              : '今天的任务都收好了。想加新的事，去目标页写一个目标。'
          }
          actionLabel="去目标页"
          actionIcon="target"
          onAction={goGoal}
        />
      );
    }

    if (filter === 'done') {
      return (
        <EmptyState
          title="今天还没有完成任务"
          body="完成一件后，它会留在这里，也可以随时撤销。"
          actionLabel="看未完成"
          actionIcon="list"
          onAction={() => setFilter('open')}
        />
      );
    }

    return (
      <EmptyState
        title="今天没有任务"
        body="去目标页写一个目标，系统会把它拆成今天能做的事。"
        actionLabel="去目标页"
        actionIcon="target"
        onAction={goGoal}
      />
    );
  }

  return (
    <View style={styles.page}>
      {actionError ? (
        <Banner
          tone="error"
          title="操作没有完成"
          body={actionError}
          onDismiss={clearActionError}
        />
      ) : null}

      {undo ? (
        <Banner
          tone="success"
          icon="check"
          title="已完成"
          body={undo.title}
          actionLabel="撤销"
          onAction={undoCompletion}
          onDismiss={dismissUndo}
        />
      ) : null}

      {deleteNotice && !actionError && !tasks.some((task) => task.id === deleteNotice.id) ? (
        <Banner
          tone="success"
          icon="check"
          title="已删除待办"
          body={`「${deleteNotice.title}」已从当前计划移除，执行记录会保留。`}
          onDismiss={() => setDeleteNotice(null)}
        />
      ) : null}

      {replanMessage ? (
        <Banner
          tone="info"
          title="重排结果"
          body={replanMessage}
          onDismiss={() => setReplanMessage(null)}
        />
      ) : null}

      <View style={styles.controls}>
        <View style={styles.controlsRow}>
          <View style={styles.viewSwitch}>
            <Segmented
              options={VIEWS}
              value={view}
              onChange={(index) => {
                setView(index);
                setActiveId(null);
              }}
            />
          </View>
          <View style={styles.controlsActions}>
            <Button label="添加" icon="plus" variant="filled" onPress={handleAdd} />
            <Button
              label={planChanges.length > 0 ? `计划变更 · ${planChanges.length}` : '计划变更'}
              variant="tonal"
              icon="calendar"
              onPress={() => setChangeOpen(true)}
            />
          </View>
        </View>

        <View style={styles.filterRow}>
          <View style={styles.filterGroup}>
            {FILTERS.map((item) => (
              <TaskFilterChip
                key={item.key}
                label={item.label}
                selected={filter === item.key}
                count={
                  item.key === 'all'
                    ? allToday.length
                    : item.key === 'open'
                      ? openTodayCount
                      : doneTodayCount
                }
                onPress={() => {
                  setFilter(item.key);
                  setActiveId(null);
                }}
              />
            ))}
            {view === 0 ? (
              <TaskFilterChip
                label="按分组"
                icon="swap"
                selected={grouped}
                onPress={() => setGrouped((value) => !value)}
              />
            ) : null}
          </View>
          <Button
            label={replanBusy ? '重排中…' : '重排计划'}
            variant="outlined"
            icon="swap"
            disabled={replanBusy}
            onPress={() => setReplanConfirmOpen(true)}
          />
        </View>

        {replanBusy ? (
          <Text style={[styles.replanNote, { color: colors.inkMuted }]}>
            正在重排，新版本会替换当前计划；旧版本会保留。
          </Text>
        ) : null}
      </View>

      <ScheduleSection onOverlayChange={setScheduleOverlayOpen} />

      {view === 0 ? (
        <View style={styles.body} testID="todo-list">
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

          {todayTasks.length === 0 && overdueTasks.length === 0 ? renderEmpty() : null}
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
          共 <Text style={styles.mono}>{stats.openCount}</Text> 件未完成 · 今日{' '}
          <Text style={styles.mono}>
            {stats.todayDone}/{stats.todayTotal}
          </Text>{' '}
          · 连续 <Text style={styles.mono}>{stats.streak}</Text> 天
        </Text>
        <Button label="写今日反馈" variant="filled" onPress={() => router.push('/feedback')} />
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
      {quickAddOpen ? (
        <QuickTaskDialog
          onClose={() => setQuickAddOpen(false)}
          onCreate={(input) => {
            createTask(input);
            setQuickAddOpen(false);
          }}
        />
      ) : null}

      {detailTask ? (
        <TaskDetailSheet
          key={detailTask.id}
          task={detailTask}
          canEdit={canEditTasks}
          goalTitle={
            detailTask.goalId == null
              ? null
              : (goals.find((goal) => goal.id === detailTask.goalId)?.title ?? null)
          }
          onClose={() => setDetailId(null)}
          onUpdateTask={updateTask}
          onUpdateStandard={updateStandard}
          onToggleDone={(id) => {
            handleToggleById(id);
            setDetailId(null);
          }}
          onSetSkipped={(id, skipped) => {
            setSkipped(id, skipped);
            setDetailId(null);
          }}
          onMoveTomorrow={(id) => {
            moveBy(id, 1);
            setDetailId(null);
          }}
          onRequestDelete={requestDelete}
        />
      ) : null}

      <Dialog
        visible={addHintOpen}
        title="在目标页添加并拆解"
        description="新任务要先在「目标」页写下来，再交给系统拆成每天能做的事。这里不会空白新建任务。"
        onRequestClose={() => setAddHintOpen(false)}
        actions={[
          { label: '取消', variant: 'text', onPress: () => setAddHintOpen(false) },
          { label: '去目标页', variant: 'filled', onPress: goGoal },
        ]}
      />

      <Dialog
        visible={replanConfirmOpen}
        title="重排这一版计划？"
        description="会基于今天的完成情况和状态生成新一版计划。旧版本会保留，反馈记录也不会丢。"
        onRequestClose={() => setReplanConfirmOpen(false)}
        actions={[
          { label: '取消', variant: 'text', onPress: () => setReplanConfirmOpen(false) },
          {
            label: '开始重排',
            variant: 'filled',
            onPress: () => {
              void runReplan();
            },
          },
        ]}
      />

      <Dialog
        visible={deleteTargetId != null}
        title="删除这个待办？"
        description="删除后不会出现在当前计划里，执行记录会保留。确定删除？"
        onRequestClose={() => setDeleteTargetId(null)}
        actions={[
          { label: '取消', variant: 'text', onPress: () => setDeleteTargetId(null) },
          { label: '删除', variant: 'filled', onPress: confirmDelete },
        ]}>
        {deleteTargetTask ? (
          <View
            style={[
              styles.deleteSummary,
              {
                borderColor: colors.outlineVariant,
                backgroundColor: colors.surfaceContainerLow,
              },
            ]}>
            <Text style={[styles.deleteTitle, { color: colors.ink }]} numberOfLines={2}>
              {deleteTargetTask.title}
            </Text>
            <Text style={[styles.deleteMeta, { color: colors.inkMuted }]}>
              任务 #{deleteTargetTask.id}
            </Text>
          </View>
        ) : null}
      </Dialog>
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
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.md,
  },
  viewSwitch: {
    flexGrow: 1,
    flexBasis: 220,
    maxWidth: 360,
  },
  controlsActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: Space.sm,
  },
  filterRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Space.sm,
  },
  filterGroup: {
    flexGrow: 1,
    minWidth: 0,
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: Space.sm,
  },
  replanNote: {
    fontSize: Type.labelMedium,
    lineHeight: Type.labelMedium * Line.relaxed,
  },
  body: {
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
  deleteSummary: {
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: Space.md,
    gap: Space.xs,
  },
  deleteTitle: {
    fontSize: Type.bodyLarge,
    lineHeight: Type.bodyLarge * Line.normal,
    fontWeight: '600',
  },
  deleteMeta: {
    fontFamily: Fonts.monoRegular,
    fontSize: Type.labelMedium,
  },
});
